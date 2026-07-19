"""``WorkflowRunRepository``: append-mostly CRUD over
:class:`~cerebrum.infrastructure.database.models.workflow_run.WorkflowRun`
— CIS Phase 5 Prompt 2's Execution History and Retry Failed Workflows
(the latest failed run's id/state to retry from). Mirrors
cerebrum.repositories.postgres.connector_sync_run_repository.ConnectorSyncRunRepository's
exact shape.
"""

import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.workflow_run import (
    WorkflowRun,
    WorkflowRunStatus,
)
from cerebrum.repositories.contracts import Page, Pagination


class WorkflowRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> WorkflowRun | None:
        return await self._session.get(WorkflowRun, entity_id)

    async def add(self, entity: WorkflowRun) -> WorkflowRun:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: WorkflowRun) -> WorkflowRun:
        await self._session.flush()
        return entity

    async def get_latest_for_workflow(
        self, workflow_id: uuid.UUID
    ) -> WorkflowRun | None:
        statement = (
            select(WorkflowRun)
            .where(WorkflowRun.workflow_id == workflow_id)
            .order_by(desc(WorkflowRun.started_at))
            .limit(1)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_failed_for_workflow(
        self, workflow_id: uuid.UUID
    ) -> WorkflowRun | None:
        """Retry Failed Workflows' lookup — the most recent run that
        ended in :attr:`~WorkflowRunStatus.FAILED`.
        """
        statement = (
            select(WorkflowRun)
            .where(
                WorkflowRun.workflow_id == workflow_id,
                WorkflowRun.status == WorkflowRunStatus.FAILED.value,
            )
            .order_by(desc(WorkflowRun.started_at))
            .limit(1)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_workflow(
        self, workflow_id: uuid.UUID, *, pagination: Pagination
    ) -> Page[WorkflowRun]:
        base_statement = select(WorkflowRun).where(
            WorkflowRun.workflow_id == workflow_id
        )
        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = base_statement.order_by(desc(WorkflowRun.started_at))
        statement = statement.offset(pagination.offset).limit(pagination.page_size)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)
