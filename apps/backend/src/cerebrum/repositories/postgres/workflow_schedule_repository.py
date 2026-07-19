"""``WorkflowScheduleRepository``: CRUD, soft delete, and due-query over
:class:`~cerebrum.infrastructure.database.models.workflow_schedule.WorkflowSchedule`
— CIS Phase 5 Prompt 2's Scheduler (Cron Scheduling, One-Time
Execution). Mirrors
cerebrum.repositories.postgres.connector_repository.ConnectorRepository's
shape, with :meth:`list_due` replacing that repository's
``list_due_for_sync``.
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.workflow_schedule import (
    ScheduleStatus,
    WorkflowSchedule,
)
from cerebrum.utils.clock import utcnow


class WorkflowScheduleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> WorkflowSchedule | None:
        schedule = await self._session.get(WorkflowSchedule, entity_id)
        return None if schedule is None or schedule.is_deleted else schedule

    async def add(self, entity: WorkflowSchedule) -> WorkflowSchedule:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: WorkflowSchedule) -> WorkflowSchedule:
        await self._session.flush()
        return entity

    async def soft_delete(self, entity_id: uuid.UUID) -> None:
        schedule = await self._session.get(WorkflowSchedule, entity_id)
        if schedule is not None:
            schedule.is_deleted = True
            schedule.deleted_at = utcnow()
            await self._session.flush()

    async def list_due(self, *, as_of: datetime) -> list[WorkflowSchedule]:
        """CIS Phase 5 Prompt 2's Cron Scheduling/One-Time Execution —
        every non-deleted, :attr:`~ScheduleStatus.ACTIVE` schedule whose
        ``next_run_at`` has arrived, across every workspace — see
        cerebrum.application.workflows.scheduler for why this is a
        query a caller polls rather than a timer this codebase itself
        runs, and why workspace narrowing happens after this call, not
        in it (mirrors
        cerebrum.repositories.postgres.connector_repository.ConnectorRepository.list_due_for_sync
        exactly).
        """
        statement = select(WorkflowSchedule).where(
            WorkflowSchedule.is_deleted.is_(False),
            WorkflowSchedule.status == ScheduleStatus.ACTIVE.value,
            WorkflowSchedule.next_run_at.is_not(None),
            WorkflowSchedule.next_run_at <= as_of,
        )
        result = await self._session.execute(statement)
        return list(result.scalars())

    async def list_by_workflow(self, workflow_id: uuid.UUID) -> list[WorkflowSchedule]:
        statement = select(WorkflowSchedule).where(
            WorkflowSchedule.workflow_id == workflow_id,
            WorkflowSchedule.is_deleted.is_(False),
        )
        result = await self._session.execute(statement)
        return list(result.scalars())
