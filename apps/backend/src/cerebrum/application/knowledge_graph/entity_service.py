"""``EntityService``: CRUD, soft delete/restore, and dedup-aware
creation over
:class:`~cerebrum.infrastructure.database.models.entity.Entity` — CIS
Phase 3 Prompt 1's Knowledge Graph & Entity Intelligence.
"""

import uuid
from typing import Any

from cerebrum.application.knowledge_graph.deduplication import (
    DEFAULT_SIMILARITY_THRESHOLD,
    find_duplicate,
)
from cerebrum.infrastructure.database.models.entity import Entity, EntityType
from cerebrum.infrastructure.entities.results import ExtractedEntity
from cerebrum.repositories.contracts import (
    FilterOperator,
    FilterSpec,
    Page,
    Pagination,
    SortSpec,
)
from cerebrum.repositories.postgres.entity_repository import EntityRepository
from cerebrum.shared.errors.exceptions import NotFoundException
from cerebrum.utils.clock import utcnow


class EntityService:
    def __init__(self, *, entity_repository: EntityRepository) -> None:
        self._entities = entity_repository

    async def get(self, entity_id: uuid.UUID, *, workspace_id: uuid.UUID) -> Entity:
        entity = await self._entities.get_by_id(entity_id)
        if entity is None or entity.workspace_id != workspace_id:
            raise NotFoundException(f"No entity with id {entity_id}.")
        return entity

    async def create(
        self,
        *,
        workspace_id: uuid.UUID,
        organization_id: uuid.UUID,
        entity_type: EntityType,
        canonical_name: str,
        custom_type_name: str | None = None,
        aliases: list[str] | None = None,
        description: str | None = None,
        confidence: float = 1.0,
        created_by: uuid.UUID | None = None,
    ) -> Entity:
        entity = Entity(
            workspace_id=workspace_id,
            organization_id=organization_id,
            entity_type=entity_type.value,
            custom_type_name=custom_type_name,
            canonical_name=canonical_name,
            aliases=aliases or [],
            description=description,
            confidence=confidence,
            created_by=created_by,
            updated_by=created_by,
        )
        return await self._entities.add(entity)

    async def update(
        self,
        entity_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        canonical_name: str | None = None,
        aliases: list[str] | None = None,
        description: str | None = None,
        updated_by: uuid.UUID | None = None,
    ) -> Entity:
        entity = await self.get(entity_id, workspace_id=workspace_id)
        if canonical_name is not None:
            entity.canonical_name = canonical_name
        if aliases is not None:
            entity.aliases = aliases
        if description is not None:
            entity.description = description
        entity.updated_by = updated_by
        return await self._entities.update(entity)

    async def soft_delete(
        self, entity_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> None:
        await self.get(entity_id, workspace_id=workspace_id)
        await self._entities.soft_delete(entity_id)

    async def restore(self, entity_id: uuid.UUID, *, workspace_id: uuid.UUID) -> Entity:
        entity = await self._entities.get_by_id_including_deleted(entity_id)
        if entity is None or entity.workspace_id != workspace_id:
            raise NotFoundException(f"No entity with id {entity_id}.")
        await self._entities.restore(entity_id)
        restored = await self._entities.get_by_id(entity_id)
        assert restored is not None
        return restored

    async def list_in_workspace(
        self,
        *,
        workspace_id: uuid.UUID,
        pagination: Pagination,
        filters: list[FilterSpec] | None = None,
        sort: list[SortSpec] | None = None,
    ) -> Page[Entity]:
        scoped_filters = [
            FilterSpec(
                field="workspace_id", operator=FilterOperator.EQ, value=workspace_id
            ),
            *(filters or []),
        ]
        return await self._entities.list(
            pagination=pagination, filters=scoped_filters, sort=sort
        )

    async def list_by_source_chunks(
        self, chunk_ids: list[uuid.UUID], *, workspace_id: uuid.UUID
    ) -> list[Entity]:
        """Backs
        cerebrum.application.knowledge_graph.knowledge_graph_service.KnowledgeGraphService's
        version-aware re-processing — see that service's docstring.
        """
        entities = await self._entities.list_by_source_chunk_ids(chunk_ids)
        return [e for e in entities if e.workspace_id == workspace_id]

    async def get_history(
        self, entity_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """CIS Phase 3 Prompt 1's Entity History API: the accumulated
        :attr:`~cerebrum.infrastructure.database.models.entity.Entity.provenance`
        list — every extraction run that has ever contributed to this
        entity, in the order it happened.
        """
        entity = await self.get(entity_id, workspace_id=workspace_id)
        return entity.provenance

    async def upsert_from_extraction(
        self,
        candidate: ExtractedEntity,
        *,
        workspace_id: uuid.UUID,
        organization_id: uuid.UUID,
        source_chunk_id: uuid.UUID | None,
        source_document_id: uuid.UUID | None,
        extractor_name: str,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        created_by: uuid.UUID | None = None,
    ) -> tuple[Entity, bool]:
        """Resolves ``candidate`` against existing entities of the same
        type in this workspace and either merges into a match (new
        alias if the extracted name differs, raised confidence if
        higher, a new provenance record appended) or creates a new
        :class:`~cerebrum.infrastructure.database.models.entity.Entity`
        — CIS Phase 3 Prompt 1's Deduplication. Returns ``(entity,
        was_created)``.
        """
        candidates = await self._entities.list_by_workspace_and_type(
            workspace_id=workspace_id,
            entity_type=candidate.entity_type.value,
            custom_type_name=candidate.custom_type_name,
        )
        match = find_duplicate(
            candidate, candidates, similarity_threshold=similarity_threshold
        )

        provenance_record = {
            "chunk_id": str(source_chunk_id) if source_chunk_id else None,
            "document_id": str(source_document_id) if source_document_id else None,
            "confidence": candidate.confidence,
            "extractor": extractor_name,
            "extracted_at": utcnow().isoformat(),
        }

        if match is not None:
            if (
                candidate.canonical_name.strip().casefold()
                != match.canonical_name.strip().casefold()
                and candidate.canonical_name not in match.aliases
            ):
                match.aliases = [*match.aliases, candidate.canonical_name]
            if candidate.confidence > match.confidence:
                match.confidence = candidate.confidence
            match.provenance = [*match.provenance, provenance_record]
            match.source_chunk_id = source_chunk_id or match.source_chunk_id
            match.source_document_id = source_document_id or match.source_document_id
            await self._entities.update(match)
            return match, False

        entity = Entity(
            workspace_id=workspace_id,
            organization_id=organization_id,
            entity_type=candidate.entity_type.value,
            custom_type_name=candidate.custom_type_name,
            canonical_name=candidate.canonical_name,
            aliases=[],
            description=None,
            confidence=candidate.confidence,
            source_chunk_id=source_chunk_id,
            source_document_id=source_document_id,
            provenance=[provenance_record],
            created_by=created_by,
            updated_by=created_by,
        )
        await self._entities.add(entity)
        return entity, True
