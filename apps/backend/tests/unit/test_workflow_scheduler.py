"""Proves CIS Phase 5 Prompt 2's ``WorkflowScheduler`` — Cron
Scheduling, One-Time Execution, and the due-run poll
``run_due_workflows`` delegates to
``WorkflowRunService.execute(..., trigger_type=SCHEDULED)`` for. See
that scheduler module's own docstring for why there is no separate
schedule-level pause — CIS Phase 5 Prompt 1's ``ConnectorScheduler``
tests (test_connector_scheduler.py) establish the identical "a query to
poll, not a timer to own" testing pattern this file mirrors.
"""

import uuid
from datetime import timedelta
from typing import Any

import pytest
from _auth_factories import create_organization, create_user, create_workspace
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.auth.audit_service import AuditService
from cerebrum.application.workflows.scheduler import WorkflowScheduler
from cerebrum.application.workflows.step_executors import StepOutcome
from cerebrum.application.workflows.workflow_run_service import WorkflowRunService
from cerebrum.application.workflows.workflow_service import WorkflowService
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.workflow_run import WorkflowRunStatus
from cerebrum.infrastructure.database.models.workflow_schedule import (
    ScheduleStatus,
    ScheduleType,
    WorkflowSchedule,
)
from cerebrum.infrastructure.database.models.workflow_version import (
    StepType,
    TriggerType,
)
from cerebrum.repositories.postgres.audit_repository import AuditEventRepository
from cerebrum.repositories.postgres.workflow_repository import WorkflowRepository
from cerebrum.repositories.postgres.workflow_run_repository import WorkflowRunRepository
from cerebrum.repositories.postgres.workflow_schedule_repository import (
    WorkflowScheduleRepository,
)
from cerebrum.repositories.postgres.workflow_step_run_repository import (
    WorkflowStepRunRepository,
)
from cerebrum.repositories.postgres.workflow_version_repository import (
    WorkflowVersionRepository,
)
from cerebrum.shared.errors.exceptions import ValidationException
from cerebrum.utils.clock import utcnow

pytestmark = pytest.mark.unit


def _hasher():  # type: ignore[no-untyped-def]
    from cerebrum.config.security import SecuritySettings
    from cerebrum.infrastructure.security.password import PasswordHasher

    return PasswordHasher(SecuritySettings())


async def _tenant(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    unique = uuid.uuid4().hex[:8]
    org = await create_organization(session, slug=f"acme-{unique}")
    workspace = await create_workspace(session, organization_id=org.id)
    user = await create_user(
        session,
        organization_id=org.id,
        email=f"alice-{unique}@acme.example",
        password="CorrectHorse123!",
        hasher=_hasher(),
    )
    await session.commit()
    return org.id, workspace.id, user.id


class _NoOpExecutor:
    async def execute(  # type: ignore[no-untyped-def]
        self, config: dict[str, Any], *, workspace_id, triggered_by, context
    ) -> StepOutcome:
        return StepOutcome(output={})


def _workflow_service(session: AsyncSession) -> WorkflowService:
    return WorkflowService(
        workflow_repository=WorkflowRepository(session),
        workflow_version_repository=WorkflowVersionRepository(session),
        event_dispatcher=EventDispatcher(),
        audit_service=AuditService(AuditEventRepository(session)),
    )


def _run_service(session: AsyncSession) -> WorkflowRunService:
    return WorkflowRunService(
        workflow_service=_workflow_service(session),
        workflow_version_repository=WorkflowVersionRepository(session),
        workflow_run_repository=WorkflowRunRepository(session),
        workflow_step_run_repository=WorkflowStepRunRepository(session),
        step_executors={step_type: _NoOpExecutor() for step_type in StepType},  # type: ignore[misc]
        event_dispatcher=EventDispatcher(),
        audit_service=AuditService(AuditEventRepository(session)),
    )


def _scheduler(session: AsyncSession) -> WorkflowScheduler:
    return WorkflowScheduler(
        schedule_repository=WorkflowScheduleRepository(session),
        run_service=_run_service(session),
        audit_service=AuditService(AuditEventRepository(session)),
    )


async def _create_workflow(  # type: ignore[no-untyped-def]
    session: AsyncSession, *, workspace_id, organization_id, user_id
):
    workflow = await _workflow_service(session).create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="Scheduled digest",
        description=None,
        trigger_type=TriggerType.SCHEDULED,
        trigger_config={},
        steps=[{"id": "notify", "type": "notification", "config": {"message": "hi"}}],
        created_by=user_id,
    )
    await session.commit()
    return workflow


async def test_create_schedule_cron_computes_next_run_at(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    workflow = await _create_workflow(
        db_session,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
    )
    scheduler = _scheduler(db_session)

    schedule = await scheduler.create_schedule(
        workflow.id,
        workspace_id=workspace_id,
        schedule_type=ScheduleType.CRON,
        cron_expression="*/5 * * * *",
        created_by=user_id,
    )
    await db_session.commit()

    assert schedule.status == ScheduleStatus.ACTIVE.value
    assert schedule.next_run_at is not None
    assert schedule.next_run_at > utcnow()


async def test_create_schedule_cron_rejects_invalid_expression(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    workflow = await _create_workflow(
        db_session,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
    )
    scheduler = _scheduler(db_session)

    with pytest.raises(ValidationException):
        await scheduler.create_schedule(
            workflow.id,
            workspace_id=workspace_id,
            schedule_type=ScheduleType.CRON,
            cron_expression="not a cron",
            created_by=user_id,
        )


async def test_create_schedule_one_time_requires_run_at(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    workflow = await _create_workflow(
        db_session,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
    )
    scheduler = _scheduler(db_session)

    with pytest.raises(ValidationException):
        await scheduler.create_schedule(
            workflow.id,
            workspace_id=workspace_id,
            schedule_type=ScheduleType.ONE_TIME,
            created_by=user_id,
        )


async def test_list_schedules_and_delete_schedule(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    workflow = await _create_workflow(
        db_session,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
    )
    scheduler = _scheduler(db_session)
    schedule = await scheduler.create_schedule(
        workflow.id,
        workspace_id=workspace_id,
        schedule_type=ScheduleType.ONE_TIME,
        run_at=utcnow() + timedelta(hours=1),
        created_by=user_id,
    )
    await db_session.commit()

    schedules = await scheduler.list_schedules(workflow.id, workspace_id=workspace_id)
    assert [s.id for s in schedules] == [schedule.id]

    await scheduler.delete_schedule(
        schedule.id, workspace_id=workspace_id, deleted_by=user_id
    )
    await db_session.commit()

    assert await scheduler.list_schedules(workflow.id, workspace_id=workspace_id) == []


async def test_run_due_workflows_fires_due_one_time_schedule_and_completes_it(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    workflow = await _create_workflow(
        db_session,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
    )
    scheduler = _scheduler(db_session)
    schedule = await WorkflowScheduleRepository(db_session).add(
        WorkflowSchedule(
            workflow_id=workflow.id,
            workspace_id=workspace_id,
            schedule_type=ScheduleType.ONE_TIME.value,
            run_at=utcnow() - timedelta(minutes=1),
            status=ScheduleStatus.ACTIVE.value,
            next_run_at=utcnow() - timedelta(minutes=1),
        )
    )
    await db_session.commit()

    runs = await scheduler.run_due_workflows()
    await db_session.commit()

    assert len(runs) == 1
    assert runs[0].workflow_id == workflow.id
    assert runs[0].trigger_type == TriggerType.SCHEDULED.value
    assert runs[0].status == WorkflowRunStatus.COMPLETED.value

    refreshed = await WorkflowScheduleRepository(db_session).get_by_id(schedule.id)
    assert refreshed.status == ScheduleStatus.COMPLETED.value
    assert refreshed.next_run_at is None
    assert refreshed.last_run_at is not None


async def test_run_due_workflows_advances_cron_schedule(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    workflow = await _create_workflow(
        db_session,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
    )
    scheduler = _scheduler(db_session)
    schedule = await scheduler.create_schedule(
        workflow.id,
        workspace_id=workspace_id,
        schedule_type=ScheduleType.CRON,
        cron_expression="* * * * *",
        created_by=user_id,
    )
    schedule.next_run_at = utcnow() - timedelta(minutes=1)
    await WorkflowScheduleRepository(db_session).update(schedule)
    await db_session.commit()

    runs = await scheduler.run_due_workflows()
    await db_session.commit()

    assert len(runs) == 1
    refreshed = await WorkflowScheduleRepository(db_session).get_by_id(schedule.id)
    assert refreshed.status == ScheduleStatus.ACTIVE.value
    assert refreshed.last_run_at is not None
    # croniter's get_next always returns strictly after the instant it
    # was asked to advance from — the real invariant to check, since a
    # "* * * * *" expression evaluated moments apart can otherwise land
    # on the very same next-minute boundary and make an inequality
    # assertion against a separately-computed timestamp flaky.
    assert refreshed.next_run_at is not None
    assert refreshed.next_run_at > refreshed.last_run_at


async def test_run_due_workflows_filters_by_workspace(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    _, other_workspace_id, other_user_id = await _tenant(db_session)
    workflow = await _create_workflow(
        db_session,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
    )
    other_workflow = await _create_workflow(
        db_session,
        workspace_id=other_workspace_id,
        organization_id=organization_id,
        user_id=other_user_id,
    )
    scheduler = _scheduler(db_session)
    schedule_repo = WorkflowScheduleRepository(db_session)
    await schedule_repo.add(
        WorkflowSchedule(
            workflow_id=workflow.id,
            workspace_id=workspace_id,
            schedule_type=ScheduleType.ONE_TIME.value,
            run_at=utcnow() - timedelta(minutes=1),
            status=ScheduleStatus.ACTIVE.value,
            next_run_at=utcnow() - timedelta(minutes=1),
        )
    )
    await schedule_repo.add(
        WorkflowSchedule(
            workflow_id=other_workflow.id,
            workspace_id=other_workspace_id,
            schedule_type=ScheduleType.ONE_TIME.value,
            run_at=utcnow() - timedelta(minutes=1),
            status=ScheduleStatus.ACTIVE.value,
            next_run_at=utcnow() - timedelta(minutes=1),
        )
    )
    await db_session.commit()

    runs = await scheduler.run_due_workflows(workspace_id=workspace_id)
    await db_session.commit()

    assert len(runs) == 1
    assert runs[0].workflow_id == workflow.id


async def test_list_due_delegates_to_repository(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    workflow = await _create_workflow(
        db_session,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
    )
    scheduler = _scheduler(db_session)
    schedule = await scheduler.create_schedule(
        workflow.id,
        workspace_id=workspace_id,
        schedule_type=ScheduleType.ONE_TIME,
        run_at=utcnow() - timedelta(minutes=1),
        created_by=user_id,
    )
    schedule.next_run_at = utcnow() - timedelta(minutes=1)
    await WorkflowScheduleRepository(db_session).update(schedule)
    await db_session.commit()

    due = await scheduler.list_due()

    assert [s.id for s in due] == [schedule.id]
