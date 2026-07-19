"""``RelationshipService``: CRUD, soft delete/restore, and dedup-aware
creation over
:class:`~cerebrum.infrastructure.database.models.relationship.Relationship`
— CIS Phase 3 Prompt 1's Knowledge Graph & Entity Intelligence.
"""

import uuid

from cerebrum.infrastructure.database.models.relationship import (
    Relationship,
    RelationshipType,
)
from cerebrum.infrastructure.relationships.results import ExtractedRelationship
from cerebrum.repositories.contracts import (
    FilterOperator,
    FilterSpec,
    Page,
    Pagination,
    SortSpec,
)
from cerebrum.repositories.postgres.relationship_repository import (
    RelationshipRepository,
)
from cerebrum.shared.errors.exceptions import NotFoundException


class RelationshipService:
    def __init__(self, *, relationship_repository: RelationshipRepository) -> None:
        self._relationships = relationship_repository

    async def get(
        self, relationship_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> Relationship:
        relationship = await self._relationships.get_by_id(relationship_id)
        if relationship is None or relationship.workspace_id != workspace_id:
            raise NotFoundException(f"No relationship with id {relationship_id}.")
        return relationship

    async def create(
        self,
        *,
        workspace_id: uuid.UUID,
        organization_id: uuid.UUID,
        source_entity_id: uuid.UUID,
        target_entity_id: uuid.UUID,
        relationship_type: RelationshipType,
        custom_type_name: str | None = None,
        confidence: float = 1.0,
        evidence: str | None = None,
        created_by: uuid.UUID | None = None,
    ) -> Relationship:
        relationship = Relationship(
            workspace_id=workspace_id,
            organization_id=organization_id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relationship_type=relationship_type.value,
            custom_type_name=custom_type_name,
            confidence=confidence,
            evidence=evidence,
            created_by=created_by,
            updated_by=created_by,
        )
        return await self._relationships.add(relationship)

    async def update(
        self,
        relationship_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        confidence: float | None = None,
        evidence: str | None = None,
        updated_by: uuid.UUID | None = None,
    ) -> Relationship:
        relationship = await self.get(relationship_id, workspace_id=workspace_id)
        if confidence is not None:
            relationship.confidence = confidence
        if evidence is not None:
            relationship.evidence = evidence
        relationship.updated_by = updated_by
        return await self._relationships.update(relationship)

    async def soft_delete(
        self, relationship_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> None:
        await self.get(relationship_id, workspace_id=workspace_id)
        await self._relationships.soft_delete(relationship_id)

    async def restore(
        self, relationship_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> Relationship:
        relationship = await self._relationships.get_by_id_including_deleted(
            relationship_id
        )
        if relationship is None or relationship.workspace_id != workspace_id:
            raise NotFoundException(f"No relationship with id {relationship_id}.")
        await self._relationships.restore(relationship_id)
        restored = await self._relationships.get_by_id(relationship_id)
        assert restored is not None
        return restored

    async def list_in_workspace(
        self,
        *,
        workspace_id: uuid.UUID,
        pagination: Pagination,
        filters: list[FilterSpec] | None = None,
        sort: list[SortSpec] | None = None,
    ) -> Page[Relationship]:
        scoped_filters = [
            FilterSpec(
                field="workspace_id", operator=FilterOperator.EQ, value=workspace_id
            ),
            *(filters or []),
        ]
        return await self._relationships.list(
            pagination=pagination, filters=scoped_filters, sort=sort
        )

    async def list_for_entity(
        self, entity_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> list[Relationship]:
        relationships = await self._relationships.list_for_entity(entity_id)
        return [r for r in relationships if r.workspace_id == workspace_id]

    async def list_by_source_chunks(
        self, chunk_ids: list[uuid.UUID], *, workspace_id: uuid.UUID
    ) -> list[Relationship]:
        """Mirrors
        cerebrum.application.knowledge_graph.entity_service.EntityService.list_by_source_chunks.
        """
        relationships = await self._relationships.list_by_source_chunk_ids(chunk_ids)
        return [r for r in relationships if r.workspace_id == workspace_id]

    async def upsert_from_extraction(
        self,
        candidate: ExtractedRelationship,
        *,
        source_entity_id: uuid.UUID,
        target_entity_id: uuid.UUID,
        workspace_id: uuid.UUID,
        organization_id: uuid.UUID,
        source_chunk_id: uuid.UUID | None,
        source_document_id: uuid.UUID | None,
        created_by: uuid.UUID | None = None,
    ) -> tuple[Relationship, bool]:
        """Duplicate prevention — CIS Phase 3 Prompt 1's Deduplication,
        applied to relationships: the same typed edge between the same
        two entities is strengthened (confidence/evidence updated if
        the new extraction is more confident), not duplicated. Returns
        ``(relationship, was_created)``.
        """
        existing = await self._relationships.find_existing(
            workspace_id=workspace_id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relationship_type=candidate.relationship_type.value,
        )
        if existing is not None:
            if candidate.confidence > existing.confidence:
                existing.confidence = candidate.confidence
                existing.evidence = candidate.evidence
            existing.source_chunk_id = source_chunk_id or existing.source_chunk_id
            existing.source_document_id = (
                source_document_id or existing.source_document_id
            )
            await self._relationships.update(existing)
            return existing, False

        relationship = Relationship(
            workspace_id=workspace_id,
            organization_id=organization_id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relationship_type=candidate.relationship_type.value,
            custom_type_name=candidate.custom_type_name,
            confidence=candidate.confidence,
            evidence=candidate.evidence,
            source_chunk_id=source_chunk_id,
            source_document_id=source_document_id,
            created_by=created_by,
            updated_by=created_by,
        )
        await self._relationships.add(relationship)
        return relationship, True
