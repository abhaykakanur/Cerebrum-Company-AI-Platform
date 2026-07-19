"""``KnowledgeGraphRepository``: Neo4j node/relationship persistence for
:class:`~cerebrum.infrastructure.database.models.entity.Entity`/
:class:`~cerebrum.infrastructure.database.models.relationship.Relationship`
— CIS Phase 3 Prompt 1's Knowledge Graph integration. PostgreSQL (see
cerebrum.repositories.postgres.entity_repository/relationship_repository)
remains the system of record for attributes/tenant-scoping/audit; this
repository keeps the graph a synchronized projection of it, written to
only by
cerebrum.application.knowledge_graph.knowledge_graph_service.KnowledgeGraphService
— see :class:`~cerebrum.infrastructure.database.models.entity.Entity`'s
docstring for that split.

Every node/relationship carries the same ``id`` its PostgreSQL row has
(as a string — Neo4j has no native UUID type), so a graph query result
can always be resolved back to the authoritative row. ``MERGE`` (not
``CREATE``) throughout makes every write idempotent — replaying an
extraction run twice for the same entity/relationship ``id`` updates
the existing node/edge rather than creating a duplicate.
"""

import uuid
from typing import Any

from neo4j import AsyncDriver

from cerebrum.utils.clock import utcnow


class KnowledgeGraphRepository:
    def __init__(self, driver: AsyncDriver) -> None:
        self._driver = driver

    async def ensure_constraints(self) -> None:
        """Idempotent — safe to call on every startup, not just once.
        Not required for correctness (every write here already
        ``MERGE``s on ``id``), only for query/write performance once
        the graph holds more than a trivial number of nodes.
        """
        async with self._driver.session() as session:
            await session.run(
                "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS "
                "FOR (e:Entity) REQUIRE e.id IS UNIQUE"
            )

    async def upsert_entity_node(
        self,
        *,
        entity_id: uuid.UUID,
        workspace_id: uuid.UUID,
        entity_type: str,
        canonical_name: str,
        aliases: list[str],
        confidence: float,
    ) -> None:
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (e:Entity {id: $id})
                SET e.workspace_id = $workspace_id,
                    e.entity_type = $entity_type,
                    e.canonical_name = $canonical_name,
                    e.aliases = $aliases,
                    e.confidence = $confidence,
                    e.is_deleted = false,
                    e.updated_at = $updated_at
                """,
                id=str(entity_id),
                workspace_id=str(workspace_id),
                entity_type=entity_type,
                canonical_name=canonical_name,
                aliases=aliases,
                confidence=confidence,
                updated_at=utcnow().isoformat(),
            )

    async def soft_delete_entity_node(self, entity_id: uuid.UUID) -> None:
        """Soft-delete propagation — CIS Phase 3 Prompt 1's requirement.
        Marks the node (and every relationship edge touching it)
        deleted rather than issuing ``DETACH DELETE``: a hard delete
        would destroy graph structure a future query might still want
        (e.g. "what did this entity used to connect to before it was
        removed"), the same reasoning
        cerebrum.infrastructure.database.models.mixins.SoftDeleteMixin's
        docstring gives for the PostgreSQL side.
        """
        async with self._driver.session() as session:
            await session.run(
                """
                MATCH (e:Entity {id: $id})
                SET e.is_deleted = true, e.deleted_at = $deleted_at
                WITH e
                MATCH (e)-[r:RELATES_TO]-()
                SET r.is_deleted = true
                """,
                id=str(entity_id),
                deleted_at=utcnow().isoformat(),
            )

    async def upsert_relationship_edge(
        self,
        *,
        relationship_id: uuid.UUID,
        source_entity_id: uuid.UUID,
        target_entity_id: uuid.UUID,
        relationship_type: str,
        confidence: float,
    ) -> None:
        async with self._driver.session() as session:
            await session.run(
                """
                MATCH (source:Entity {id: $source_id})
                MATCH (target:Entity {id: $target_id})
                MERGE (source)-[r:RELATES_TO {id: $id}]->(target)
                SET r.relationship_type = $relationship_type,
                    r.confidence = $confidence,
                    r.is_deleted = false,
                    r.updated_at = $updated_at
                """,
                id=str(relationship_id),
                source_id=str(source_entity_id),
                target_id=str(target_entity_id),
                relationship_type=relationship_type,
                confidence=confidence,
                updated_at=utcnow().isoformat(),
            )

    async def soft_delete_relationship_edge(self, relationship_id: uuid.UUID) -> None:
        async with self._driver.session() as session:
            await session.run(
                "MATCH ()-[r:RELATES_TO {id: $id}]->() SET r.is_deleted = true",
                id=str(relationship_id),
            )

    async def get_neighbors(
        self, entity_id: uuid.UUID, *, depth: int = 1
    ) -> list[dict[str, Any]]:
        """Every distinct non-deleted :class:`Entity` node within
        ``depth`` relationship hops of ``entity_id`` (undirected — a
        neighbor is a neighbor regardless of edge direction), excluding
        ``entity_id`` itself. ``depth`` is interpolated into the
        Cypher pattern's ``*1..depth`` range, not parameterized —
        Neo4j's Cypher has no syntax for parameterizing a variable-
        length path's bounds; ``depth`` comes from
        cerebrum.api.v1.entities's route (a validated ``int`` FastAPI
        path/query parameter, never raw user text), so this is not the
        injection risk string-interpolating a ``WHERE``/``MATCH``
        *value* would be.
        """
        query = (
            f"MATCH (e:Entity {{id: $id}})-[r:RELATES_TO*1..{int(depth)}]-"
            "(neighbor:Entity) "
            "WHERE neighbor.is_deleted = false AND neighbor.id <> $id "
            "RETURN DISTINCT neighbor"
        )
        async with self._driver.session() as session:
            result = await session.run(query, id=str(entity_id))
            records = [record async for record in result]
            return [dict(record["neighbor"]) for record in records]

    async def get_statistics(self, workspace_id: uuid.UUID) -> dict[str, int]:
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (e:Entity {workspace_id: $workspace_id, is_deleted: false})
                OPTIONAL MATCH (e)-[r:RELATES_TO {is_deleted: false}]->()
                RETURN count(DISTINCT e) AS entity_count, count(r) AS relationship_count
                """,
                workspace_id=str(workspace_id),
            )
            record = await result.single()
            if record is None:
                return {"entity_count": 0, "relationship_count": 0}
            return {
                "entity_count": record["entity_count"],
                "relationship_count": record["relationship_count"],
            }

    async def validate_consistency(self, workspace_id: uuid.UUID) -> list[str]:
        """Graph consistency validation — CIS Phase 3 Prompt 1's
        requirement, scoped to the one consistency property this
        milestone's PostgreSQL/Neo4j dual-write could actually violate:
        a relationship edge whose source or target node is (or has
        become) soft-deleted. Not a full graph-theory validator — a
        concrete, checkable invariant; an empty list means consistent.
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (source:Entity)-[r:RELATES_TO {is_deleted: false}]
                    ->(target:Entity)
                WHERE source.workspace_id = $workspace_id
                  AND (source.is_deleted = true OR target.is_deleted = true)
                RETURN r.id AS relationship_id
                """,
                workspace_id=str(workspace_id),
            )
            records = [record async for record in result]
            return [
                f"Relationship {record['relationship_id']} references a deleted "
                f"entity node."
                for record in records
            ]
