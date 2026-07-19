"""``WorkflowStepRunRepository``: CRUD and by-run listing over
:class:`~cerebrum.infrastructure.database.models.workflow_step_run.WorkflowStepRun`
— CIS Phase 5 Prompt 2's Step Duration/Success Rate/Failure Reason
observability.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.workflow_step_run import WorkflowStepRun


class WorkflowStepRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> WorkflowStepRun | None:
        return await self._session.get(WorkflowStepRun, entity_id)

    async def add(self, entity: WorkflowStepRun) -> WorkflowStepRun:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: WorkflowStepRun) -> WorkflowStepRun:
        await self._session.flush()
        return entity

    async def list_by_run(self, workflow_run_id: uuid.UUID) -> list[WorkflowStepRun]:
        statement = (
            select(WorkflowStepRun)
            .where(WorkflowStepRun.workflow_run_id == workflow_run_id)
            .order_by(WorkflowStepRun.started_at)
        )
        result = await self._session.execute(statement)
        return list(result.scalars())
