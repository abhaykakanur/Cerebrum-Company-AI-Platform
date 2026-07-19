"""Proves CIS Phase 5 Prompt 2's Execution Engine,
``WorkflowRunService``: Sequential Execution, Conditional Branching,
Delay, Retry, Timeout, Parallel Execution (topology-level — see that
module's own docstring for why not wall-clock concurrency),
Cancellation, Progress Tracking (``WorkflowStepRun`` rows), Retry Failed
Workflows, and event-triggered dispatch — against a real, SQLite-backed
``WorkflowService``/repositories (see test_workflow_repository.py's
docstring) with every :class:`StepExecutor` replaced by a fully
controllable fake, since this milestone only needs to prove the
*engine*, not re-prove what test_workflow_step_executors.py already
covers for the real executors.
"""

import asyncio
import uuid
from typing import Any

import pytest
from _auth_factories import create_organization, create_user, create_workspace
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.auth.audit_service import AuditService
from cerebrum.application.workflows.events import (
    WorkflowCompletedEvent,
    WorkflowFailedEvent,
)
from cerebrum.application.workflows.step_executors import (
    StepExecutionError,
    StepOutcome,
)
from cerebrum.application.workflows.template import ExecutionContext
from cerebrum.application.workflows.workflow_run_service import WorkflowRunService
from cerebrum.application.workflows.workflow_service import WorkflowService
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.workflow import WorkflowStatus
from cerebrum.infrastructure.database.models.workflow_run import WorkflowRunStatus
from cerebrum.infrastructure.database.models.workflow_step_run import (
    WorkflowStepRunStatus,
)
from cerebrum.infrastructure.database.models.workflow_version import (
    StepType,
    TriggerType,
)
from cerebrum.repositories.contracts import Pagination
from cerebrum.repositories.postgres.audit_repository import AuditEventRepository
from cerebrum.repositories.postgres.workflow_repository import WorkflowRepository
from cerebrum.repositories.postgres.workflow_run_repository import WorkflowRunRepository
from cerebrum.repositories.postgres.workflow_step_run_repository import (
    WorkflowStepRunRepository,
)
from cerebrum.repositories.postgres.workflow_version_repository import (
    WorkflowVersionRepository,
)
from cerebrum.shared.errors.exceptions import ValidationException

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


class _FakeExecutor:
    """Scripted per-step-id behavior: a step whose ``id`` is a key in
    ``responses`` returns/raises whatever was scripted; unscripted
    steps succeed with an empty output. Records every call so tests can
    assert on invocation order/count without depending on real service
    behavior.
    """

    def __init__(self) -> None:
        self.responses: dict[str, list[Any]] = {}
        self.calls: list[str] = []

    def script(self, step_id: str, *outcomes: Any) -> None:
        self.responses[step_id] = list(outcomes)

    async def execute(
        self,
        config: dict[str, Any],
        *,
        workspace_id,
        triggered_by,
        context: ExecutionContext,
    ) -> StepOutcome:
        step_id = str(config.get("_step_id", "unknown"))
        self.calls.append(step_id)
        scripted = self.responses.get(step_id)
        if scripted:
            outcome = scripted.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        return StepOutcome(output={})


def _step(
    step_id: str,
    step_type: StepType = StepType.NOTIFICATION,
    *,
    config: dict[str, Any] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    base_config = {"_step_id": step_id, "message": "test", **(config or {})}
    step = {"id": step_id, "type": step_type.value, "config": base_config}
    step.update(overrides)
    return step


def _service(
    session: AsyncSession,
    *,
    executor: _FakeExecutor,
    events: EventDispatcher | None = None,
) -> WorkflowRunService:
    events = events or EventDispatcher()
    audit = AuditService(AuditEventRepository(session))
    workflow_service = WorkflowService(
        workflow_repository=WorkflowRepository(session),
        workflow_version_repository=WorkflowVersionRepository(session),
        event_dispatcher=events,
        audit_service=audit,
    )
    return WorkflowRunService(
        workflow_service=workflow_service,
        workflow_version_repository=WorkflowVersionRepository(session),
        workflow_run_repository=WorkflowRunRepository(session),
        workflow_step_run_repository=WorkflowStepRunRepository(session),
        step_executors=dict.fromkeys(StepType, executor),  # type: ignore[misc]
        event_dispatcher=events,
        audit_service=audit,
    )


async def _create_workflow(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    steps: list[dict[str, Any]],
    trigger_type: TriggerType = TriggerType.MANUAL,
):
    workflow_service = WorkflowService(
        workflow_repository=WorkflowRepository(session),
        workflow_version_repository=WorkflowVersionRepository(session),
        event_dispatcher=EventDispatcher(),
        audit_service=AuditService(AuditEventRepository(session)),
    )
    workflow = await workflow_service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="Test workflow",
        description=None,
        trigger_type=trigger_type,
        trigger_config={},
        steps=steps,
        created_by=user_id,
    )
    await session.commit()
    return workflow


async def test_execute_runs_sequential_steps_and_completes(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    executor = _FakeExecutor()
    executor.script("step_one", StepOutcome(output={"n": 1}))
    executor.script("step_two", StepOutcome(output={"n": 2}))
    events = EventDispatcher()
    completed: list[WorkflowCompletedEvent] = []
    events.subscribe(WorkflowCompletedEvent, completed.append)
    service = _service(db_session, executor=executor, events=events)

    workflow = await _create_workflow(
        db_session,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        steps=[
            _step("step_one", output_variable="first"),
            _step("step_two", output_variable="second"),
        ],
    )

    run = await service.execute(
        workflow.id, workspace_id=workspace_id, triggered_by=user_id
    )
    await db_session.commit()

    assert run.status == WorkflowRunStatus.COMPLETED.value
    assert executor.calls == ["step_one", "step_two"]
    assert run.variables["first"] == {"n": 1}
    assert run.variables["second"] == {"n": 2}
    assert len(completed) == 1

    step_runs = await service.list_step_runs(run.id, workspace_id=workspace_id)
    assert [s.status for s in step_runs] == [
        WorkflowStepRunStatus.COMPLETED.value,
        WorkflowStepRunStatus.COMPLETED.value,
    ]


async def test_execute_raises_when_workflow_paused(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    executor = _FakeExecutor()
    service = _service(db_session, executor=executor)
    workflow = await _create_workflow(
        db_session,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        steps=[_step("step_one")],
    )
    workflow_service = WorkflowService(
        workflow_repository=WorkflowRepository(db_session),
        workflow_version_repository=WorkflowVersionRepository(db_session),
        event_dispatcher=EventDispatcher(),
        audit_service=AuditService(AuditEventRepository(db_session)),
    )
    await workflow_service.change_status(
        workflow.id,
        workspace_id=workspace_id,
        status=WorkflowStatus.PAUSED,
        updated_by=user_id,
    )
    await db_session.commit()

    with pytest.raises(ValidationException):
        await service.execute(
            workflow.id, workspace_id=workspace_id, triggered_by=user_id
        )


async def test_execute_marks_run_failed_and_stops_on_step_failure(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    executor = _FakeExecutor()
    executor.script("step_one", StepExecutionError("boom"))
    events = EventDispatcher()
    failed: list[WorkflowFailedEvent] = []
    events.subscribe(WorkflowFailedEvent, failed.append)
    service = _service(db_session, executor=executor, events=events)
    workflow = await _create_workflow(
        db_session,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        steps=[_step("step_one"), _step("step_two")],
    )

    run = await service.execute(
        workflow.id, workspace_id=workspace_id, triggered_by=user_id
    )
    await db_session.commit()

    assert run.status == WorkflowRunStatus.FAILED.value
    assert run.error_message is not None
    assert executor.calls == ["step_one"]
    assert len(failed) == 1


async def test_execute_continues_past_failure_when_on_failure_continue(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    executor = _FakeExecutor()
    executor.script("step_one", StepExecutionError("boom"))
    service = _service(db_session, executor=executor)
    workflow = await _create_workflow(
        db_session,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        steps=[_step("step_one", on_failure="continue"), _step("step_two")],
    )

    run = await service.execute(
        workflow.id, workspace_id=workspace_id, triggered_by=user_id
    )
    await db_session.commit()

    assert run.status == WorkflowRunStatus.COMPLETED.value
    assert executor.calls == ["step_one", "step_two"]


async def test_execute_retries_before_succeeding(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    executor = _FakeExecutor()
    executor.script(
        "step_one", StepExecutionError("flaky"), StepOutcome(output={"ok": True})
    )
    service = _service(db_session, executor=executor)
    workflow = await _create_workflow(
        db_session,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        steps=[_step("step_one", retry={"max_attempts": 2, "backoff_seconds": 0})],
    )

    run = await service.execute(
        workflow.id, workspace_id=workspace_id, triggered_by=user_id
    )
    await db_session.commit()

    assert run.status == WorkflowRunStatus.COMPLETED.value
    assert executor.calls == ["step_one", "step_one"]
    step_runs = await service.list_step_runs(run.id, workspace_id=workspace_id)
    assert step_runs[0].attempt == 2


async def test_execute_step_timeout_fails_the_step(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)

    class _SlowExecutor:
        async def execute(  # type: ignore[no-untyped-def]
            self, config, *, workspace_id, triggered_by, context
        ) -> StepOutcome:
            await asyncio.sleep(10)
            return StepOutcome(output={})

    service = WorkflowRunService(
        workflow_service=WorkflowService(
            workflow_repository=WorkflowRepository(db_session),
            workflow_version_repository=WorkflowVersionRepository(db_session),
            event_dispatcher=EventDispatcher(),
            audit_service=AuditService(AuditEventRepository(db_session)),
        ),
        workflow_version_repository=WorkflowVersionRepository(db_session),
        workflow_run_repository=WorkflowRunRepository(db_session),
        workflow_step_run_repository=WorkflowStepRunRepository(db_session),
        step_executors={step_type: _SlowExecutor() for step_type in StepType},  # type: ignore[misc]
        event_dispatcher=EventDispatcher(),
        audit_service=AuditService(AuditEventRepository(db_session)),
    )
    workflow = await _create_workflow(
        db_session,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        steps=[_step("step_one", timeout_seconds=0.05)],
    )

    run = await service.execute(
        workflow.id, workspace_id=workspace_id, triggered_by=user_id
    )
    await db_session.commit()

    assert run.status == WorkflowRunStatus.FAILED.value
    assert "timed out" in (run.error_message or "")


async def test_execute_condition_routes_to_then_and_else(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    executor = _FakeExecutor()
    service = _service(db_session, executor=executor)
    steps = [
        {
            "id": "check",
            "type": StepType.CONDITION.value,
            "config": {
                "condition": {"left": 5, "operator": "gt", "right": 1},
                "then": [_step("then_step")],
                "else": [_step("else_step")],
            },
        }
    ]
    workflow = await _create_workflow(
        db_session,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        steps=steps,
    )

    run = await service.execute(
        workflow.id, workspace_id=workspace_id, triggered_by=user_id
    )
    await db_session.commit()

    assert run.status == WorkflowRunStatus.COMPLETED.value
    assert executor.calls == ["then_step"]


async def test_execute_delay_step_completes(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    executor = _FakeExecutor()
    service = _service(db_session, executor=executor)
    workflow = await _create_workflow(
        db_session,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        steps=[
            {"id": "wait", "type": StepType.DELAY.value, "config": {"seconds": 0.01}},
        ],
    )

    run = await service.execute(
        workflow.id, workspace_id=workspace_id, triggered_by=user_id
    )
    await db_session.commit()

    assert run.status == WorkflowRunStatus.COMPLETED.value
    step_runs = await service.list_step_runs(run.id, workspace_id=workspace_id)
    assert step_runs[0].output == {"seconds": 0.01}


async def test_execute_delay_step_caps_at_max_delay_seconds(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    executor = _FakeExecutor()
    service = _service(db_session, executor=executor)
    recorded: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        recorded.append(seconds)

    monkeypatch.setattr(
        "cerebrum.application.workflows.workflow_run_service.asyncio.sleep", _fake_sleep
    )
    workflow = await _create_workflow(
        db_session,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        steps=[
            {"id": "wait", "type": StepType.DELAY.value, "config": {"seconds": 999}},
        ],
    )

    await service.execute(workflow.id, workspace_id=workspace_id, triggered_by=user_id)
    await db_session.commit()

    assert recorded == [30.0]


async def test_execute_parallel_runs_every_branch_and_aggregates_failure(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    executor = _FakeExecutor()
    executor.script("branch_b", StepExecutionError("branch b failed"))
    service = _service(db_session, executor=executor)
    steps = [
        {
            "id": "fan_out",
            "type": StepType.PARALLEL.value,
            "config": {"steps": [_step("branch_a"), _step("branch_b")]},
        }
    ]
    workflow = await _create_workflow(
        db_session,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        steps=steps,
    )

    run = await service.execute(
        workflow.id, workspace_id=workspace_id, triggered_by=user_id
    )
    await db_session.commit()

    assert run.status == WorkflowRunStatus.FAILED.value
    assert set(executor.calls) == {"branch_a", "branch_b"}


async def test_cancel_moves_running_run_to_cancelled(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    executor = _FakeExecutor()
    service = _service(db_session, executor=executor)
    workflow = await _create_workflow(
        db_session,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        steps=[_step("step_one")],
    )
    run = await service.execute(
        workflow.id, workspace_id=workspace_id, triggered_by=user_id
    )
    await db_session.commit()
    assert run.status == WorkflowRunStatus.COMPLETED.value

    # Simulate a run orphaned mid-flight by a crashed process.
    run.status = WorkflowRunStatus.RUNNING.value
    await WorkflowRunRepository(db_session).update(run)
    await db_session.commit()

    cancelled = await service.cancel(run.id, workspace_id=workspace_id)
    await db_session.commit()

    assert cancelled.status == WorkflowRunStatus.CANCELLED.value


async def test_cancel_rejects_a_non_running_run(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    executor = _FakeExecutor()
    service = _service(db_session, executor=executor)
    workflow = await _create_workflow(
        db_session,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        steps=[_step("step_one")],
    )
    run = await service.execute(
        workflow.id, workspace_id=workspace_id, triggered_by=user_id
    )
    await db_session.commit()

    with pytest.raises(ValidationException):
        await service.cancel(run.id, workspace_id=workspace_id)


async def test_retry_run_skips_completed_top_level_steps(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    executor = _FakeExecutor()
    executor.script("step_two", StepExecutionError("boom"))
    service = _service(db_session, executor=executor)
    workflow = await _create_workflow(
        db_session,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        steps=[_step("step_one", output_variable="first"), _step("step_two")],
    )

    failed_run = await service.execute(
        workflow.id, workspace_id=workspace_id, triggered_by=user_id
    )
    await db_session.commit()
    assert failed_run.status == WorkflowRunStatus.FAILED.value
    assert executor.calls == ["step_one", "step_two"]

    executor.calls.clear()
    retried_run = await service.retry_run(
        failed_run.id, workspace_id=workspace_id, triggered_by=user_id
    )
    await db_session.commit()

    assert retried_run.status == WorkflowRunStatus.COMPLETED.value
    # step_one already completed in the failed run — retry only re-runs
    # the remaining top-level step.
    assert executor.calls == ["step_two"]
    assert retried_run.variables["first"] == {}


async def test_retry_run_rejects_a_non_failed_run(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    executor = _FakeExecutor()
    service = _service(db_session, executor=executor)
    workflow = await _create_workflow(
        db_session,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        steps=[_step("step_one")],
    )
    run = await service.execute(
        workflow.id, workspace_id=workspace_id, triggered_by=user_id
    )
    await db_session.commit()

    with pytest.raises(ValidationException):
        await service.retry_run(run.id, workspace_id=workspace_id, triggered_by=user_id)


async def test_dispatch_event_starts_runs_for_matching_active_workflows(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    executor = _FakeExecutor()
    service = _service(db_session, executor=executor)
    matching = await _create_workflow(
        db_session,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        steps=[_step("step_one")],
        trigger_type=TriggerType.CUSTOM_EVENT,
    )
    await _create_workflow(
        db_session,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        steps=[_step("step_two")],
        trigger_type=TriggerType.MANUAL,
    )

    runs = await service.dispatch_event(
        TriggerType.CUSTOM_EVENT.value,
        workspace_id=workspace_id,
        payload={"reason": "test"},
    )
    await db_session.commit()

    assert len(runs) == 1
    assert runs[0].workflow_id == matching.id
    assert runs[0].trigger_context == {"reason": "test"}


async def test_list_runs_and_get_run(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    executor = _FakeExecutor()
    service = _service(db_session, executor=executor)
    workflow = await _create_workflow(
        db_session,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        steps=[_step("step_one")],
    )
    run = await service.execute(
        workflow.id, workspace_id=workspace_id, triggered_by=user_id
    )
    await db_session.commit()

    fetched = await service.get_run(run.id, workspace_id=workspace_id)
    assert fetched.id == run.id

    page = await service.list_runs(
        workflow.id,
        workspace_id=workspace_id,
        pagination=Pagination(page=1, page_size=50),
    )
    assert page.total_items == 1
