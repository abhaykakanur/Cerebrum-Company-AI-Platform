"""``CapsuleGraphService``: CIS Phase 5 Prompt 3's Knowledge Graph
Integration — extends the *existing* CIS Phase 3 knowledge graph with
employee expertise/ownership/collaboration edges, rather than building
a parallel graph store. Every write goes through
cerebrum.application.knowledge_graph.entity_service.EntityService/
cerebrum.application.knowledge_graph.relationship_service.RelationshipService
(PostgreSQL, the system of record) and then mirrors into Neo4j via
:class:`~cerebrum.repositories.neo4j.knowledge_graph_repository.KnowledgeGraphRepository`
— the exact "write Postgres, then mirror Neo4j" sequence
cerebrum.application.knowledge_graph.knowledge_graph_service.KnowledgeGraphService
already established for extraction-produced entities/relationships,
applied here to capsule-produced ones instead of introducing a second
write path into the same two stores.

Ownership/collaboration edges reuse
:class:`~cerebrum.infrastructure.relationships.results.ExtractedRelationship`
purely as the parameter shape ``RelationshipService.upsert_from_extraction``
already accepts — ``source_index``/``target_index`` are unused by that
method once real entity ids are supplied, so this is the dedup-aware
upsert path (repeated capsule refreshes strengthen an existing edge
rather than duplicating it), not a re-implementation of it.
"""

import uuid

from cerebrum.application.knowledge_graph.entity_service import EntityService
from cerebrum.application.knowledge_graph.relationship_service import (
    RelationshipService,
)
from cerebrum.infrastructure.database.models.entity import Entity, EntityType
from cerebrum.infrastructure.database.models.relationship import (
    Relationship,
    RelationshipType,
)
from cerebrum.infrastructure.relationships.results import ExtractedRelationship
from cerebrum.repositories.neo4j.knowledge_graph_repository import (
    KnowledgeGraphRepository,
)
from cerebrum.shared.errors.exceptions import ValidationException


class CapsuleGraphService:
    def __init__(
        self,
        *,
        entity_service: EntityService,
        relationship_service: RelationshipService,
        graph_repository: KnowledgeGraphRepository,
    ) -> None:
        self._entities = entity_service
        self._relationships = relationship_service
        self._graph = graph_repository

    async def create_person_entity(
        self,
        *,
        workspace_id: uuid.UUID,
        organization_id: uuid.UUID,
        canonical_name: str,
        created_by: uuid.UUID | None,
    ) -> Entity:
        entity = await self._entities.create(
            workspace_id=workspace_id,
            organization_id=organization_id,
            entity_type=EntityType.PERSON,
            canonical_name=canonical_name,
            created_by=created_by,
        )
        await self._mirror_entity(entity)
        return entity

    async def get_person_entity(
        self, entity_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> Entity:
        entity = await self._entities.get(entity_id, workspace_id=workspace_id)
        if entity.entity_type != EntityType.PERSON.value:
            raise ValidationException(
                f"Entity {entity_id} is not a person entity "
                f"(entity_type={entity.entity_type})."
            )
        return entity

    async def upsert_edge(
        self,
        *,
        source_entity_id: uuid.UUID,
        target_entity_id: uuid.UUID,
        relationship_type: RelationshipType,
        workspace_id: uuid.UUID,
        organization_id: uuid.UUID,
        confidence: float,
        evidence_text: str,
        created_by: uuid.UUID | None,
    ) -> Relationship:
        candidate = ExtractedRelationship(
            source_index=0,
            target_index=0,
            relationship_type=relationship_type,
            confidence=confidence,
            evidence=evidence_text,
        )
        relationship, _was_created = await self._relationships.upsert_from_extraction(
            candidate,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            workspace_id=workspace_id,
            organization_id=organization_id,
            source_chunk_id=None,
            source_document_id=None,
            created_by=created_by,
        )
        await self._mirror_relationship(relationship)
        return relationship

    async def _mirror_entity(self, entity: Entity) -> None:
        await self._graph.upsert_entity_node(
            entity_id=entity.id,
            workspace_id=entity.workspace_id,
            entity_type=entity.entity_type,
            canonical_name=entity.canonical_name,
            aliases=entity.aliases,
            confidence=entity.confidence,
        )

    async def _mirror_relationship(self, relationship: Relationship) -> None:
        await self._graph.upsert_relationship_edge(
            relationship_id=relationship.id,
            source_entity_id=relationship.source_entity_id,
            target_entity_id=relationship.target_entity_id,
            relationship_type=relationship.relationship_type,
            confidence=relationship.confidence,
        )
