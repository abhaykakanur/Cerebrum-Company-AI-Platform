"""``KnowledgeGraphService``: CIS Phase 3 Prompt 1's pipeline extension
— Chunk -> Entity Extraction -> Relationship Extraction -> Graph Update
-> Knowledge Ready. Runs entity/relationship extraction over every
chunk of a document version, resolves each candidate through
:class:`~cerebrum.application.knowledge_graph.entity_service.EntityService`/
:class:`~cerebrum.application.knowledge_graph.relationship_service.RelationshipService`'s
dedup-aware upserts, mirrors the result into Neo4j via
:class:`~cerebrum.repositories.neo4j.knowledge_graph_repository.KnowledgeGraphRepository`,
and emits the three CIS Phase 3 Prompt 1 events.

Called by
cerebrum.application.knowledge.knowledge_preparation_service.KnowledgePreparationService.prepare
after Chunking succeeds — the same synchronous, no-worker-yet execution
model every stage since CIS Phase 2 Prompt 3 has used.

**Version-aware graph updates**: before creating anything, this service
soft-deletes any existing entity/relationship whose ``source_chunk_id``
already belongs to this document version's *current* chunk set (see
:meth:`EntityService.list_by_source_chunks`) — i.e., whatever a prior
run against this exact chunk set produced. Because
cerebrum.application.knowledge.chunking_service.ChunkingService already
deletes and wholly replaces a version's chunks on every re-chunk, a
genuine re-chunk-then-reprocess naturally starts from an empty stale
set (the old chunk IDs no longer exist); a bare retry against the same
chunk set instead supersedes exactly what that retry is replacing —
either way, results never accumulate duplicates across repeated runs.
"""

import uuid
from dataclasses import dataclass
from typing import Any

from cerebrum.application.knowledge_graph.entity_service import EntityService
from cerebrum.application.knowledge_graph.events import (
    EntityExtractedEvent,
    GraphUpdatedEvent,
    RelationshipExtractedEvent,
)
from cerebrum.application.knowledge_graph.relationship_service import (
    RelationshipService,
)
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.document_version import DocumentVersion
from cerebrum.infrastructure.entities.extractors import EntityExtractor
from cerebrum.infrastructure.relationships.extractors import RelationshipExtractor
from cerebrum.repositories.neo4j.knowledge_graph_repository import (
    KnowledgeGraphRepository,
)
from cerebrum.repositories.postgres.chunk_repository import ChunkRepository
from cerebrum.repositories.postgres.document_repository import DocumentRepository
from cerebrum.repositories.postgres.document_version_repository import (
    DocumentVersionRepository,
)
from cerebrum.repositories.postgres.workspace_repository import WorkspaceRepository
from cerebrum.shared.errors.exceptions import NotFoundException


@dataclass(frozen=True, slots=True)
class GraphUpdateResult:
    entity_count: int
    relationship_count: int


class KnowledgeGraphService:
    def __init__(
        self,
        *,
        entity_service: EntityService,
        relationship_service: RelationshipService,
        graph_repository: KnowledgeGraphRepository,
        chunk_repository: ChunkRepository,
        version_repository: DocumentVersionRepository,
        document_repository: DocumentRepository,
        workspace_repository: WorkspaceRepository,
        entity_extractor: EntityExtractor,
        relationship_extractor: RelationshipExtractor,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._entities = entity_service
        self._relationships = relationship_service
        self._graph = graph_repository
        self._chunks = chunk_repository
        self._versions = version_repository
        self._documents = document_repository
        self._workspaces = workspace_repository
        self._entity_extractor = entity_extractor
        self._relationship_extractor = relationship_extractor
        self._events = event_dispatcher

    async def process_version(
        self,
        document_version_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        created_by: uuid.UUID | None = None,
    ) -> GraphUpdateResult:
        version = await self._require_version_in_workspace(
            document_version_id, workspace_id=workspace_id
        )
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise NotFoundException(f"No workspace with id {workspace_id}.")
        organization_id = workspace.organization_id
        chunks = await self._chunks.list_by_document_version(document_version_id)
        chunk_ids = [chunk.id for chunk in chunks]

        await self._supersede_prior_run(chunk_ids, workspace_id=workspace_id)

        entity_count = 0
        relationship_count = 0
        for chunk in chunks:
            extracted_entities = self._entity_extractor.extract(chunk.text)
            entity_id_by_index: dict[int, uuid.UUID] = {}

            for index, candidate in enumerate(extracted_entities):
                entity, was_created = await self._entities.upsert_from_extraction(
                    candidate,
                    workspace_id=workspace_id,
                    organization_id=organization_id,
                    source_chunk_id=chunk.id,
                    source_document_id=version.document_id,
                    extractor_name=type(self._entity_extractor).__name__,
                    created_by=created_by,
                )
                entity_id_by_index[index] = entity.id
                await self._graph.upsert_entity_node(
                    entity_id=entity.id,
                    workspace_id=workspace_id,
                    entity_type=entity.entity_type,
                    canonical_name=entity.canonical_name,
                    aliases=entity.aliases,
                    confidence=entity.confidence,
                )
                self._events.publish(
                    EntityExtractedEvent(
                        entity_id=entity.id,
                        workspace_id=workspace_id,
                        entity_type=entity.entity_type,
                        was_created=was_created,
                    )
                )
                entity_count += 1

            extracted_relationships = self._relationship_extractor.extract(
                chunk.text, extracted_entities
            )
            for relationship_candidate in extracted_relationships:
                source_id = entity_id_by_index.get(relationship_candidate.source_index)
                target_id = entity_id_by_index.get(relationship_candidate.target_index)
                if source_id is None or target_id is None or source_id == target_id:
                    continue
                (
                    relationship,
                    relationship_was_created,
                ) = await self._relationships.upsert_from_extraction(
                    relationship_candidate,
                    source_entity_id=source_id,
                    target_entity_id=target_id,
                    workspace_id=workspace_id,
                    organization_id=organization_id,
                    source_chunk_id=chunk.id,
                    source_document_id=version.document_id,
                    created_by=created_by,
                )
                await self._graph.upsert_relationship_edge(
                    relationship_id=relationship.id,
                    source_entity_id=source_id,
                    target_entity_id=target_id,
                    relationship_type=relationship.relationship_type,
                    confidence=relationship.confidence,
                )
                self._events.publish(
                    RelationshipExtractedEvent(
                        relationship_id=relationship.id,
                        workspace_id=workspace_id,
                        relationship_type=relationship.relationship_type,
                        was_created=relationship_was_created,
                    )
                )
                relationship_count += 1

        self._events.publish(
            GraphUpdatedEvent(
                document_version_id=document_version_id,
                workspace_id=workspace_id,
                entity_count=entity_count,
                relationship_count=relationship_count,
            )
        )
        return GraphUpdateResult(
            entity_count=entity_count, relationship_count=relationship_count
        )

    async def get_neighbors(
        self, entity_id: uuid.UUID, *, workspace_id: uuid.UUID, depth: int = 1
    ) -> list[dict[str, Any]]:
        await self._entities.get(entity_id, workspace_id=workspace_id)
        return await self._graph.get_neighbors(entity_id, depth=depth)

    async def get_statistics(self, *, workspace_id: uuid.UUID) -> dict[str, int]:
        return await self._graph.get_statistics(workspace_id)

    async def validate_consistency(self, *, workspace_id: uuid.UUID) -> list[str]:
        return await self._graph.validate_consistency(workspace_id)

    async def soft_delete_entity(
        self, entity_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> None:
        """Soft Delete Propagation — CIS Phase 3 Prompt 1's requirement:
        the one place that deletes an entity, guaranteeing PostgreSQL
        and Neo4j never disagree about whether it's deleted.
        """
        await self._entities.soft_delete(entity_id, workspace_id=workspace_id)
        await self._graph.soft_delete_entity_node(entity_id)

    async def soft_delete_relationship(
        self, relationship_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> None:
        """Mirrors :meth:`soft_delete_entity` for relationships."""
        await self._relationships.soft_delete(
            relationship_id, workspace_id=workspace_id
        )
        await self._graph.soft_delete_relationship_edge(relationship_id)

    async def _supersede_prior_run(
        self, chunk_ids: list[uuid.UUID], *, workspace_id: uuid.UUID
    ) -> None:
        stale_entities = await self._entities.list_by_source_chunks(
            chunk_ids, workspace_id=workspace_id
        )
        for stale_entity in stale_entities:
            await self._entities.soft_delete(stale_entity.id, workspace_id=workspace_id)
            await self._graph.soft_delete_entity_node(stale_entity.id)

        stale_relationships = await self._relationships.list_by_source_chunks(
            chunk_ids, workspace_id=workspace_id
        )
        for stale_relationship in stale_relationships:
            await self._relationships.soft_delete(
                stale_relationship.id, workspace_id=workspace_id
            )
            await self._graph.soft_delete_relationship_edge(stale_relationship.id)

    async def _require_version_in_workspace(
        self, document_version_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> DocumentVersion:
        version = await self._versions.get_by_id(document_version_id)
        if version is None:
            raise NotFoundException(
                f"No document version with id {document_version_id}."
            )
        document = await self._documents.get_by_id(version.document_id)
        if document is None or document.workspace_id != workspace_id:
            raise NotFoundException(
                f"No document version with id {document_version_id}."
            )
        return version
