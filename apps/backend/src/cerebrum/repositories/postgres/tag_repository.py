"""``TagRepository``: CRUD over
:class:`~cerebrum.infrastructure.database.models.tag.Tag` — CIS Phase 2
Prompt 1's Tags & Labels. Hard delete: removing a tag also removes every
:class:`~cerebrum.infrastructure.database.models.tag.DocumentTag`
assignment via the model's ``ondelete="CASCADE"``, which is the correct
behavior for a tag (unlike a Document, a Tag has no independent
existence worth preserving after deletion).
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.tag import Tag
from cerebrum.repositories.base import AbstractRepository
from cerebrum.repositories.contracts import FilterSpec, Page, Pagination, SortSpec
from cerebrum.repositories.postgres.query_utils import (
    apply_filters,
    apply_pagination,
    apply_sort,
)


class TagRepository(AbstractRepository[Tag, uuid.UUID]):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> Tag | None:
        return await self._session.get(Tag, entity_id)

    async def get_by_name(self, *, workspace_id: uuid.UUID, name: str) -> Tag | None:
        result = await self._session.execute(
            select(Tag).where(Tag.workspace_id == workspace_id, Tag.name == name)
        )
        return result.scalar_one_or_none()

    async def add(self, entity: Tag) -> Tag:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: Tag) -> Tag:
        await self._session.flush()
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        tag = await self.get_by_id(entity_id)
        if tag is not None:
            await self._session.delete(tag)
            await self._session.flush()

    async def list(
        self,
        *,
        pagination: Pagination,
        filters: list[FilterSpec] | None = None,
        sort: list[SortSpec] | None = None,
    ) -> Page[Tag]:
        base_statement = apply_filters(select(Tag), Tag, filters)

        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = apply_sort(base_statement, Tag, sort)
        statement = apply_pagination(statement, pagination)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)
