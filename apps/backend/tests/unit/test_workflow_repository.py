"""Proves CIS Phase 5 Prompt 2's ``WorkflowRepository``,
``WorkflowVersionRepository``, ``WorkflowRunRepository``,
``WorkflowStepRunRepository``, and ``WorkflowScheduleRepository``
against a real SQLite-backed session — the same "test the real SQL, not
a reimplementation of it" precedent test_connector_repository.py's
docstring explains.
"""

import uuid
from datetime import timedelta

import pytest
from _auth_factories import create_organization, create_user, create_workspace
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.workflow import Workflow, WorkflowStatus
from cerebrum.infrastructure.database.models.workflow_run import (
    WorkflowRun,
    WorkflowRunStatus,
)
from cerebrum.infrastructure.database.models.workflow_schedule import (
    ScheduleStatus,
    ScheduleType,
    WorkflowSchedule,
)
from cerebrum.infrastructure.database.models.workflow_step_run import (
    WorkflowStepRun,
    WorkflowStepRunStatus,
)
from cerebrum.infrastructure.database.models.workflow_version import (
    TriggerType,
    WorkflowVersion,
)
from cerebrum.repositories.contracts import FilterOperator, FilterSpec, Pagination
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


def _workflow(
    *, workspace_id: uuid.UUID, organization_id: uuid.UUID, **overrides
) -> Workflow:
    defaults = {
        "workspace_id": workspace_id,
        "organization_id": organization_id,
        "name": "Nightly digest",
        "status": WorkflowStatus.ACTIVE.value,
    }
    defaults.update(overrides)
    return Workflow(**defaults)


async def test_add_and_get_workflow(db_session: AsyncSession) -> None:
    organization_id, workspace_id, _user_id = await _tenant(db_session)
    repository = WorkflowRepository(db_session)

    created = await repository.add(
        _workflow(workspace_id=workspace_id, organization_id=organization_id)
    )
    await db_session.commit()

    fetched = await repository.get_by_id(created.id)
    assert fetched is not None
    assert fetched.name == "Nightly digest"


async def test_soft_delete_and_restore_workflow(db_session: AsyncSession) -> None:
    organization_id, workspace_id, _user_id = await _tenant(db_session)
    repository = WorkflowRepository(db_session)
    created = await repository.add(
        _workflow(workspace_id=workspace_id, organization_id=organization_id)
    )
    await db_session.commit()

    await repository.soft_delete(created.id)
    await db_session.commit()
    assert await repository.get_by_id(created.id) is None

    await repository.restore(created.id)
    await db_session.commit()
    assert await repository.get_by_id(created.id) is not None


async def test_list_workflow_filters_by_workspace_and_template_flag(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, _user_id = await _tenant(db_session)
    _, other_workspace_id, _ = await _tenant(db_session)
    repository = WorkflowRepository(db_session)

    live = await repository.add(
        _workflow(workspace_id=workspace_id, organization_id=organization_id)
    )
    await repository.add(
        _workflow(
            workspace_id=workspace_id,
            organization_id=organization_id,
            name="A template",
            is_template=True,
        )
    )
    await repository.add(
        _workflow(workspace_id=other_workspace_id, organization_id=organization_id)
    )
    await db_session.commit()

    page = await repository.list(
        pagination=Pagination(page=1, page_size=50),
        filters=[
            FilterSpec(
                field="workspace_id", operator=FilterOperator.EQ, value=workspace_id
            ),
            FilterSpec(field="is_template", operator=FilterOperator.EQ, value=False),
        ],
    )

    assert [w.id for w in page.items] == [live.id]


async def test_workflow_version_repository_sequencing(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    workflow = await WorkflowRepository(db_session).add(
        _workflow(workspace_id=workspace_id, organization_id=organization_id)
    )
    await db_session.commit()
    repository = WorkflowVersionRepository(db_session)

    assert await repository.get_next_version_number(workflow.id) == 1

    v1 = await repository.add(
        WorkflowVersion(
            workflow_id=workflow.id,
            version_number=1,
            trigger_type=TriggerType.MANUAL.value,
            steps=[{"id": "a", "type": "notification", "config": {"message": "hi"}}],
            created_by=user_id,
        )
    )
    await db_session.commit()
    assert await repository.get_next_version_number(workflow.id) == 2

    v2 = await repository.add(
        WorkflowVersion(
            workflow_id=workflow.id,
            version_number=2,
            trigger_type=TriggerType.MANUAL.value,
            steps=[{"id": "a", "type": "notification", "config": {"message": "bye"}}],
            created_by=user_id,
        )
    )
    await db_session.commit()

    assert (await repository.get_by_number(workflow.id, 1)).id == v1.id
    assert (await repository.get_by_number(workflow.id, 2)).id == v2.id
    assert await repository.get_by_number(workflow.id, 99) is None

    page = await repository.list_by_workflow(
        workflow.id, pagination=Pagination(page=1, page_size=50)
    )
    assert page.total_items == 2
    assert [v.id for v in page.items] == [v2.id, v1.id]


async def test_workflow_run_repository_latest_and_history(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    workflow = await WorkflowRepository(db_session).add(
        _workflow(workspace_id=workspace_id, organization_id=organization_id)
    )
    version = await WorkflowVersionRepository(db_session).add(
        WorkflowVersion(
            workflow_id=workflow.id,
            version_number=1,
            trigger_type=TriggerType.MANUAL.value,
            steps=[],
            created_by=user_id,
        )
    )
    await db_session.commit()
    repository = WorkflowRunRepository(db_session)

    older = await repository.add(
        WorkflowRun(
            workflow_id=workflow.id,
            workflow_version_id=version.id,
            workspace_id=workspace_id,
            organization_id=organization_id,
            status=WorkflowRunStatus.COMPLETED.value,
            trigger_type=TriggerType.MANUAL.value,
            started_at=utcnow() - timedelta(hours=1),
            triggered_by=user_id,
        )
    )
    newer = await repository.add(
        WorkflowRun(
            workflow_id=workflow.id,
            workflow_version_id=version.id,
            workspace_id=workspace_id,
            organization_id=organization_id,
            status=WorkflowRunStatus.FAILED.value,
            trigger_type=TriggerType.MANUAL.value,
            started_at=utcnow(),
            triggered_by=user_id,
        )
    )
    await db_session.commit()

    latest = await repository.get_latest_for_workflow(workflow.id)
    assert latest is not None and latest.id == newer.id

    latest_failed = await repository.get_latest_failed_for_workflow(workflow.id)
    assert latest_failed is not None and latest_failed.id == newer.id

    history = await repository.list_by_workflow(
        workflow.id, pagination=Pagination(page=1, page_size=50)
    )
    assert history.total_items == 2
    assert [run.id for run in history.items] == [newer.id, older.id]


async def test_workflow_step_run_repository_list_by_run(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    workflow = await WorkflowRepository(db_session).add(
        _workflow(workspace_id=workspace_id, organization_id=organization_id)
    )
    version = await WorkflowVersionRepository(db_session).add(
        WorkflowVersion(
            workflow_id=workflow.id,
            version_number=1,
            trigger_type=TriggerType.MANUAL.value,
            steps=[],
            created_by=user_id,
        )
    )
    run = await WorkflowRunRepository(db_session).add(
        WorkflowRun(
            workflow_id=workflow.id,
            workflow_version_id=version.id,
            workspace_id=workspace_id,
            organization_id=organization_id,
            status=WorkflowRunStatus.RUNNING.value,
            trigger_type=TriggerType.MANUAL.value,
            started_at=utcnow(),
        )
    )
    await db_session.commit()
    repository = WorkflowStepRunRepository(db_session)

    step_one = await repository.add(
        WorkflowStepRun(
            workflow_run_id=run.id,
            step_id="a",
            step_type="notification",
            status=WorkflowStepRunStatus.COMPLETED.value,
            started_at=utcnow() - timedelta(seconds=5),
        )
    )
    step_two = await repository.add(
        WorkflowStepRun(
            workflow_run_id=run.id,
            step_id="b",
            step_type="notification",
            status=WorkflowStepRunStatus.COMPLETED.value,
            started_at=utcnow(),
        )
    )
    await db_session.commit()

    steps = await repository.list_by_run(run.id)
    assert [s.id for s in steps] == [step_one.id, step_two.id]


async def test_workflow_schedule_repository_list_due_and_by_workflow(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    workflow = await WorkflowRepository(db_session).add(
        _workflow(workspace_id=workspace_id, organization_id=organization_id)
    )
    await db_session.commit()
    repository = WorkflowScheduleRepository(db_session)
    now = utcnow()

    due = await repository.add(
        WorkflowSchedule(
            workflow_id=workflow.id,
            workspace_id=workspace_id,
            schedule_type=ScheduleType.CRON.value,
            cron_expression="*/5 * * * *",
            status=ScheduleStatus.ACTIVE.value,
            next_run_at=now - timedelta(minutes=1),
        )
    )
    await repository.add(
        WorkflowSchedule(
            workflow_id=workflow.id,
            workspace_id=workspace_id,
            schedule_type=ScheduleType.ONE_TIME.value,
            run_at=now + timedelta(hours=1),
            status=ScheduleStatus.ACTIVE.value,
            next_run_at=now + timedelta(hours=1),
        )
    )
    await repository.add(
        WorkflowSchedule(
            workflow_id=workflow.id,
            workspace_id=workspace_id,
            schedule_type=ScheduleType.ONE_TIME.value,
            run_at=now - timedelta(hours=1),
            status=ScheduleStatus.COMPLETED.value,
            next_run_at=None,
        )
    )
    await db_session.commit()

    due_schedules = await repository.list_due(as_of=now)
    assert [s.id for s in due_schedules] == [due.id]

    all_for_workflow = await repository.list_by_workflow(workflow.id)
    assert len(all_for_workflow) == 3

    await repository.soft_delete(due.id)
    await db_session.commit()
    assert await repository.get_by_id(due.id) is None
    assert len(await repository.list_by_workflow(workflow.id)) == 2
