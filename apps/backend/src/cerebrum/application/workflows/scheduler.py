"""``WorkflowScheduler``: CIS Phase 5 Prompt 2's Scheduler — Cron
Scheduling, One-Time Execution, and Retry Failed Workflows (via
:meth:`~cerebrum.application.workflows.workflow_run_service.WorkflowRunService.retry_run`,
exposed at the API layer, not repeated here). Mirrors
cerebrum.application.connectors.scheduler.ConnectorScheduler's "a query
to poll, not a timer to own" framing exactly: no background worker
runtime exists yet (see cerebrum.config.worker.WorkerSettings), so
:meth:`run_due_workflows` is a callable an operator/cron/future-worker
invokes, not a timer this codebase runs itself. There is deliberately
no "Pause"/"Resume" here — see
cerebrum.infrastructure.database.models.workflow_schedule's docstring
for why that lives on
:attr:`~cerebrum.infrastructure.database.models.workflow.Workflow.status`
instead.
"""

import uuid
from datetime import datetime

from croniter import CroniterBadCronError, croniter

from cerebrum.application.auth.audit_service import AuditService
from cerebrum.application.workflows.workflow_run_service import WorkflowRunService
from cerebrum.infrastructure.database.models.audit import AuditEventType
from cerebrum.infrastructure.database.models.workflow_run import WorkflowRun
from cerebrum.infrastructure.database.models.workflow_schedule import (
    ScheduleStatus,
    ScheduleType,
    WorkflowSchedule,
)
from cerebrum.infrastructure.database.models.workflow_version import TriggerType
from cerebrum.repositories.postgres.workflow_schedule_repository import (
    WorkflowScheduleRepository,
)
from cerebrum.shared.errors.exceptions import NotFoundException, ValidationException
from cerebrum.utils.clock import utcnow


def _next_cron_occurrence(cron_expression: str, *, after: datetime) -> datetime:
    try:
        next_occurrence: datetime = croniter(cron_expression, after).get_next(datetime)
    except (CroniterBadCronError, ValueError) as exc:
        raise ValidationException(
            f"'{cron_expression}' is not a valid cron expression."
        ) from exc
    return next_occurrence


class WorkflowScheduler:
    def __init__(
        self,
        *,
        schedule_repository: WorkflowScheduleRepository,
        run_service: WorkflowRunService,
        audit_service: AuditService,
    ) -> None:
        self._schedules = schedule_repository
        self._runs = run_service
        self._audit = audit_service

    async def create_schedule(
        self,
        workflow_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        schedule_type: ScheduleType,
        cron_expression: str | None = None,
        run_at: datetime | None = None,
        created_by: uuid.UUID,
    ) -> WorkflowSchedule:
        if schedule_type is ScheduleType.CRON:
            if not cron_expression:
                raise ValidationException("A cron schedule requires 'cron_expression'.")
            next_run_at = _next_cron_occurrence(cron_expression, after=utcnow())
        elif schedule_type is ScheduleType.ONE_TIME:
            if run_at is None:
                raise ValidationException("A one-time schedule requires 'run_at'.")
            next_run_at = run_at
        else:  # pragma: no cover - StrEnum exhausts every value above
            raise ValidationException(f"Unknown schedule type '{schedule_type}'.")

        schedule = WorkflowSchedule(
            workflow_id=workflow_id,
            workspace_id=workspace_id,
            schedule_type=schedule_type.value,
            cron_expression=cron_expression,
            run_at=run_at,
            status=ScheduleStatus.ACTIVE.value,
            next_run_at=next_run_at,
            created_by=created_by,
        )
        await self._schedules.add(schedule)
        await self._audit.record(
            AuditEventType.WORKFLOW_SCHEDULE_CREATED,
            user_id=created_by,
            workspace_id=workspace_id,
            metadata={"workflow_id": str(workflow_id), "schedule_id": str(schedule.id)},
        )
        return schedule

    async def get_schedule(
        self, schedule_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> WorkflowSchedule:
        schedule = await self._schedules.get_by_id(schedule_id)
        if schedule is None or schedule.workspace_id != workspace_id:
            raise NotFoundException(f"No workflow schedule with id {schedule_id}.")
        return schedule

    async def list_schedules(
        self, workflow_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> list[WorkflowSchedule]:
        schedules = await self._schedules.list_by_workflow(workflow_id)
        return [
            schedule for schedule in schedules if schedule.workspace_id == workspace_id
        ]

    async def delete_schedule(
        self, schedule_id: uuid.UUID, *, workspace_id: uuid.UUID, deleted_by: uuid.UUID
    ) -> None:
        schedule = await self.get_schedule(schedule_id, workspace_id=workspace_id)
        await self._schedules.soft_delete(schedule.id)
        await self._audit.record(
            AuditEventType.WORKFLOW_SCHEDULE_DELETED,
            user_id=deleted_by,
            workspace_id=workspace_id,
            metadata={"schedule_id": str(schedule.id)},
        )

    async def list_due(self) -> list[WorkflowSchedule]:
        return await self._schedules.list_due(as_of=utcnow())

    async def run_due_workflows(
        self, *, workspace_id: uuid.UUID | None = None
    ) -> list[WorkflowRun]:
        """Runs :meth:`~WorkflowRunService.execute` (as a Scheduled
        trigger, ``triggered_by=None`` — a schedule has no acting user)
        for every due schedule, optionally narrowed to one workspace,
        then advances each fired schedule: a ``CRON`` schedule's
        ``next_run_at`` moves to its next occurrence; a ``ONE_TIME``
        schedule becomes :attr:`~ScheduleStatus.COMPLETED` (it will
        never be due again).
        """
        due = await self.list_due()
        if workspace_id is not None:
            due = [
                schedule for schedule in due if schedule.workspace_id == workspace_id
            ]

        runs: list[WorkflowRun] = []
        for schedule in due:
            run = await self._runs.execute(
                schedule.workflow_id,
                workspace_id=schedule.workspace_id,
                triggered_by=None,
                trigger_type=TriggerType.SCHEDULED,
            )
            runs.append(run)

            schedule.last_run_at = utcnow()
            if (
                schedule.schedule_type == ScheduleType.CRON.value
                and schedule.cron_expression
            ):
                schedule.next_run_at = _next_cron_occurrence(
                    schedule.cron_expression, after=schedule.last_run_at
                )
            else:
                schedule.status = ScheduleStatus.COMPLETED.value
                schedule.next_run_at = None
            await self._schedules.update(schedule)
        return runs
