"""``WorkspaceRepository``: CRUD over
:class:`~cerebrum.infrastructure.database.models.workspace.Workspace` —
see cerebrum.repositories.postgres.organization_repository's docstring
for why this concrete repository is new in CIS Phase 2 Prompt 1 despite
the model existing since Phase 1. Hard delete (no soft-delete columns on
this model — see the model's own definition); deleting a workspace is
expected to be rare and deliberate, cascading to every Folder/Document
within it per the model's ``ondelete="CASCADE"`` foreign keys.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.workspace import Workspace
from cerebrum.repositories.base import AbstractRepository
from cerebrum.repositories.contracts import FilterSpec, Page, Pagination, SortSpec
from cerebrum.repositories.postgres.query_utils import (
    apply_filters,
    apply_pagination,
    apply_sort,
)


class WorkspaceRepository(AbstractRepository[Workspace, uuid.UUID]):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> Workspace | None:
        return await self._session.get(Workspace, entity_id)

    async def get_by_slug(
        self, *, organization_id: uuid.UUID, slug: str
    ) -> Workspace | None:
        result = await self._session.execute(
            select(Workspace).where(
                Workspace.organization_id == organization_id, Workspace.slug == slug
            )
        )
        return result.scalar_one_or_none()

    async def add(self, entity: Workspace) -> Workspace:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: Workspace) -> Workspace:
        await self._session.flush()
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        workspace = await self.get_by_id(entity_id)
        if workspace is not None:
            await self._session.delete(workspace)
            await self._session.flush()

    async def list(
        self,
        *,
        pagination: Pagination,
        filters: list[FilterSpec] | None = None,
        sort: list[SortSpec] | None = None,
    ) -> Page[Workspace]:
        base_statement = apply_filters(select(Workspace), Workspace, filters)

        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = apply_sort(base_statement, Workspace, sort)
        statement = apply_pagination(statement, pagination)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)
