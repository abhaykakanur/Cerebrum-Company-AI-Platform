"""``RelationshipRepository``: CRUD, soft delete/restore, and
graph-support queries over
:class:`~cerebrum.infrastructure.database.models.relationship.Relationship`
— CIS Phase 3 Prompt 1's Knowledge Graph & Entity Intelligence.
"""

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.relationship import Relationship
from cerebrum.repositories.base import AbstractRepository
from cerebrum.repositories.contracts import FilterSpec, Page, Pagination, SortSpec
from cerebrum.repositories.postgres.query_utils import (
    apply_filters,
    apply_pagination,
    apply_sort,
)
from cerebrum.repositories.soft_delete import SoftDeleteRepository
from cerebrum.utils.clock import utcnow


class RelationshipRepository(
    AbstractRepository[Relationship, uuid.UUID],
    SoftDeleteRepository[Relationship, uuid.UUID],
):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> Relationship | None:
        relationship = await self._session.get(Relationship, entity_id)
        return None if relationship is None or relationship.is_deleted else relationship

    async def get_by_id_including_deleted(
        self, entity_id: uuid.UUID
    ) -> Relationship | None:
        return await self._session.get(Relationship, entity_id)

    async def find_existing(
        self,
        *,
        workspace_id: uuid.UUID,
        source_entity_id: uuid.UUID,
        target_entity_id: uuid.UUID,
        relationship_type: str,
    ) -> Relationship | None:
        """Duplicate prevention — CIS Phase 3 Prompt 1's Deduplication,
        applied to relationships: the same typed edge between the same
        two entities is one row, strengthened (see
        ``RelationshipService.upsert_from_extraction``) rather than
        duplicated on repeated extraction.
        """
        statement = select(Relationship).where(
            Relationship.workspace_id == workspace_id,
            Relationship.source_entity_id == source_entity_id,
            Relationship.target_entity_id == target_entity_id,
            Relationship.relationship_type == relationship_type,
            Relationship.is_deleted.is_(False),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_for_entity(self, entity_id: uuid.UUID) -> list[Relationship]:
        """Every non-deleted relationship touching ``entity_id`` as
        either endpoint — backs the Entity Neighbors API.
        """
        statement = select(Relationship).where(
            or_(
                Relationship.source_entity_id == entity_id,
                Relationship.target_entity_id == entity_id,
            ),
            Relationship.is_deleted.is_(False),
        )
        result = await self._session.execute(statement)
        return list(result.scalars())

    async def list_by_source_chunk_ids(
        self, chunk_ids: list[uuid.UUID]
    ) -> list[Relationship]:
        """Mirrors
        cerebrum.repositories.postgres.entity_repository.EntityRepository.list_by_source_chunk_ids
        — backs version-aware re-processing.
        """
        if not chunk_ids:
            return []
        statement = select(Relationship).where(
            Relationship.source_chunk_id.in_(chunk_ids),
            Relationship.is_deleted.is_(False),
        )
        result = await self._session.execute(statement)
        return list(result.scalars())

    async def add(self, entity: Relationship) -> Relationship:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: Relationship) -> Relationship:
        await self._session.flush()
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        relationship = await self.get_by_id_including_deleted(entity_id)
        if relationship is not None:
            await self._session.delete(relationship)
            await self._session.flush()

    async def soft_delete(self, entity_id: uuid.UUID) -> None:
        relationship = await self.get_by_id_including_deleted(entity_id)
        if relationship is not None:
            relationship.is_deleted = True
            relationship.deleted_at = utcnow()
            await self._session.flush()

    async def restore(self, entity_id: uuid.UUID) -> None:
        relationship = await self.get_by_id_including_deleted(entity_id)
        if relationship is not None:
            relationship.is_deleted = False
            relationship.deleted_at = None
            await self._session.flush()

    async def list(
        self,
        *,
        pagination: Pagination,
        filters: list[FilterSpec] | None = None,
        sort: list[SortSpec] | None = None,
    ) -> Page[Relationship]:
        base_statement = apply_filters(
            select(Relationship), Relationship, filters
        ).where(Relationship.is_deleted.is_(False))

        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = apply_sort(base_statement, Relationship, sort)
        statement = apply_pagination(statement, pagination)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)
