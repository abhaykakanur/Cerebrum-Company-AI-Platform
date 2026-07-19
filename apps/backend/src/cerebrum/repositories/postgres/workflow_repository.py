"""``WorkflowRepository``: CRUD and soft delete/restore over
:class:`~cerebrum.infrastructure.database.models.workflow.Workflow` —
CIS Phase 5 Prompt 2's Workflow Model. Mirrors
cerebrum.repositories.postgres.connector_repository.ConnectorRepository's
exact shape.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.workflow import Workflow
from cerebrum.repositories.base import AbstractRepository
from cerebrum.repositories.contracts import FilterSpec, Page, Pagination, SortSpec
from cerebrum.repositories.postgres.query_utils import (
    apply_filters,
    apply_pagination,
    apply_sort,
)
from cerebrum.repositories.soft_delete import SoftDeleteRepository
from cerebrum.utils.clock import utcnow


class WorkflowRepository(
    AbstractRepository[Workflow, uuid.UUID], SoftDeleteRepository[Workflow, uuid.UUID]
):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> Workflow | None:
        workflow = await self._session.get(Workflow, entity_id)
        return None if workflow is None or workflow.is_deleted else workflow

    async def get_by_id_including_deleted(
        self, entity_id: uuid.UUID
    ) -> Workflow | None:
        return await self._session.get(Workflow, entity_id)

    async def add(self, entity: Workflow) -> Workflow:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: Workflow) -> Workflow:
        await self._session.flush()
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        workflow = await self._session.get(Workflow, entity_id)
        if workflow is not None:
            await self._session.delete(workflow)
            await self._session.flush()

    async def soft_delete(self, entity_id: uuid.UUID) -> None:
        workflow = await self._session.get(Workflow, entity_id)
        if workflow is not None:
            workflow.is_deleted = True
            workflow.deleted_at = utcnow()
            await self._session.flush()

    async def restore(self, entity_id: uuid.UUID) -> None:
        workflow = await self._session.get(Workflow, entity_id)
        if workflow is not None:
            workflow.is_deleted = False
            workflow.deleted_at = None
            await self._session.flush()

    async def list(
        self,
        *,
        pagination: Pagination,
        filters: list[FilterSpec] | None = None,
        sort: list[SortSpec] | None = None,
    ) -> Page[Workflow]:
        base_statement = apply_filters(select(Workflow), Workflow, filters).where(
            Workflow.is_deleted.is_(False)
        )

        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = apply_sort(base_statement, Workflow, sort)
        statement = apply_pagination(statement, pagination)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)
