"""``EntityRepository``: CRUD, soft delete/restore, and dedup-support
queries over :class:`~cerebrum.infrastructure.database.models.entity.Entity`
— CIS Phase 3 Prompt 1's Knowledge Graph & Entity Intelligence.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.entity import Entity
from cerebrum.repositories.base import AbstractRepository
from cerebrum.repositories.contracts import FilterSpec, Page, Pagination, SortSpec
from cerebrum.repositories.postgres.query_utils import (
    apply_filters,
    apply_pagination,
    apply_sort,
)
from cerebrum.repositories.soft_delete import SoftDeleteRepository
from cerebrum.utils.clock import utcnow


class EntityRepository(
    AbstractRepository[Entity, uuid.UUID], SoftDeleteRepository[Entity, uuid.UUID]
):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> Entity | None:
        entity = await self._session.get(Entity, entity_id)
        return None if entity is None or entity.is_deleted else entity

    async def get_by_id_including_deleted(self, entity_id: uuid.UUID) -> Entity | None:
        return await self._session.get(Entity, entity_id)

    async def list_by_workspace_and_type(
        self,
        *,
        workspace_id: uuid.UUID,
        entity_type: str,
        custom_type_name: str | None = None,
    ) -> list[Entity]:
        """Every non-deleted entity of this type in this workspace —
        candidates for
        cerebrum.application.knowledge_graph.deduplication's similarity
        scan. Unpaginated, matching
        cerebrum.repositories.postgres.folder_repository.FolderRepository.list_children's
        precedent: deduplication compares against one type at a time,
        which is expected to be a bounded set, not the whole workspace.
        """
        statement = select(Entity).where(
            Entity.workspace_id == workspace_id,
            Entity.entity_type == entity_type,
            Entity.is_deleted.is_(False),
        )
        if custom_type_name is not None:
            statement = statement.where(Entity.custom_type_name == custom_type_name)
        result = await self._session.execute(statement)
        return list(result.scalars())

    async def find_exact_match(
        self,
        *,
        workspace_id: uuid.UUID,
        entity_type: str,
        canonical_name: str,
    ) -> Entity | None:
        """Exact/alias match — CIS Phase 3 Prompt 1's Deduplication:
        "Alias matching" + "Exact match". SQLite (tests) and PostgreSQL
        both support ``LOWER()``; JSON alias containment is checked in
        Python (see the loop below) since it is not portable SQL across
        those two dialects the same way a JSON-array ``LIKE`` would be.
        """
        statement = select(Entity).where(
            Entity.workspace_id == workspace_id,
            Entity.entity_type == entity_type,
            Entity.is_deleted.is_(False),
        )
        result = await self._session.execute(statement)
        candidates = list(result.scalars())
        target = canonical_name.strip().casefold()
        for candidate in candidates:
            if candidate.canonical_name.strip().casefold() == target:
                return candidate
            if any(alias.strip().casefold() == target for alias in candidate.aliases):
                return candidate
        return None

    async def list_by_source_chunk_ids(
        self, chunk_ids: list[uuid.UUID]
    ) -> list[Entity]:
        """Every non-deleted entity sourced from one of these chunks —
        backs ``KnowledgeGraphService``'s version-aware re-processing:
        find what a *previous* run against this document version
        produced, so it can be superseded rather than duplicated.
        """
        if not chunk_ids:
            return []
        statement = select(Entity).where(
            Entity.source_chunk_id.in_(chunk_ids), Entity.is_deleted.is_(False)
        )
        result = await self._session.execute(statement)
        return list(result.scalars())

    async def add(self, entity: Entity) -> Entity:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: Entity) -> Entity:
        await self._session.flush()
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        entity = await self.get_by_id_including_deleted(entity_id)
        if entity is not None:
            await self._session.delete(entity)
            await self._session.flush()

    async def soft_delete(self, entity_id: uuid.UUID) -> None:
        entity = await self.get_by_id_including_deleted(entity_id)
        if entity is not None:
            entity.is_deleted = True
            entity.deleted_at = utcnow()
            await self._session.flush()

    async def restore(self, entity_id: uuid.UUID) -> None:
        entity = await self.get_by_id_including_deleted(entity_id)
        if entity is not None:
            entity.is_deleted = False
            entity.deleted_at = None
            await self._session.flush()

    async def list(
        self,
        *,
        pagination: Pagination,
        filters: list[FilterSpec] | None = None,
        sort: list[SortSpec] | None = None,
    ) -> Page[Entity]:
        base_statement = apply_filters(select(Entity), Entity, filters).where(
            Entity.is_deleted.is_(False)
        )

        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = apply_sort(base_statement, Entity, sort)
        statement = apply_pagination(statement, pagination)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)
