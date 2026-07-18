"""``LabelRepository``: CRUD over
:class:`~cerebrum.infrastructure.database.models.label.Label` — see
cerebrum.repositories.postgres.tag_repository's docstring; identical
shape and deletion semantics, distinct table/taxonomy.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.label import Label
from cerebrum.repositories.base import AbstractRepository
from cerebrum.repositories.contracts import FilterSpec, Page, Pagination, SortSpec
from cerebrum.repositories.postgres.query_utils import (
    apply_filters,
    apply_pagination,
    apply_sort,
)


class LabelRepository(AbstractRepository[Label, uuid.UUID]):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> Label | None:
        return await self._session.get(Label, entity_id)

    async def get_by_name(self, *, workspace_id: uuid.UUID, name: str) -> Label | None:
        result = await self._session.execute(
            select(Label).where(Label.workspace_id == workspace_id, Label.name == name)
        )
        return result.scalar_one_or_none()

    async def add(self, entity: Label) -> Label:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: Label) -> Label:
        await self._session.flush()
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        label = await self.get_by_id(entity_id)
        if label is not None:
            await self._session.delete(label)
            await self._session.flush()

    async def list(
        self,
        *,
        pagination: Pagination,
        filters: list[FilterSpec] | None = None,
        sort: list[SortSpec] | None = None,
    ) -> Page[Label]:
        base_statement = apply_filters(select(Label), Label, filters)

        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = apply_sort(base_statement, Label, sort)
        statement = apply_pagination(statement, pagination)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)
