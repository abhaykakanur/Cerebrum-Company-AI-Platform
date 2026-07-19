"""``WorkflowRunService``: CIS Phase 5 Prompt 2's Execution Engine —
Sequential Execution, Parallel Execution, Conditional Branching, Retry,
Timeout, Rollback State, Cancellation, and Progress Tracking, plus
Manual/API-Request/Custom-Event triggering (see :meth:`execute` and
:meth:`dispatch_event`) and Retry Failed Workflows (see
:meth:`retry_run`).

Like
cerebrum.application.connectors.connector_sync_service.ConnectorSyncService,
this runs synchronously within one HTTP request/response cycle — no
background worker runtime exists yet (see
cerebrum.config.worker.WorkerSettings). **Progress Tracking** persists a
:class:`~cerebrum.infrastructure.database.models.workflow_step_run.WorkflowStepRun`
row per step as it starts/finishes, for the same reason
``ConnectorSyncRun`` updates its counters once per page rather than
once per item: a concurrent reader cannot observe anything before this
request's own transaction commits regardless of finer granularity.

**Parallel Execution**: every step executor shares one request-scoped
SQLAlchemy ``AsyncSession`` (see cerebrum.dependencies.workflows), which
SQLAlchemy explicitly forbids concurrent use of from multiple
coroutines. Branches of a ``parallel`` step are therefore dispatched
*sequentially*, not via ``asyncio.gather`` — "parallel" describes the
*topology* (independent branches, no ordering dependency, every branch
runs to completion regardless of a sibling's failure, failures are
aggregated rather than short-circuiting), not wall-clock concurrency.
Real I/O-level concurrency would need either a dedicated session per
branch or the background worker runtime this codebase does not yet
have. See :meth:`_execute_parallel`.

**Rollback State**: a failed run's ``variables``/``steps`` context is
persisted exactly as of the point of failure — a caller can see
precisely how far execution got — but this is state *visibility*, not
undoing any external side effect a completed step already caused (e.g.
a connector sync that already wrote documents). Generic compensation
logic for arbitrary step types is not implementable without
step-specific "undo" semantics this milestone does not define; the
same honest boundary
cerebrum.application.connectors.connector_sync_service.ConnectorSyncService.stop_sync
draws around "cannot interrupt an in-flight call."

**Cancellation**: :meth:`cancel` moves a ``RUNNING`` run straight to
``CANCELLED`` — it cannot interrupt an in-flight synchronous call from
a *different* request (there is no task to signal); its real purpose,
exactly like ``stop_sync``, is clearing a run stuck ``RUNNING`` after a
crashed process so a fresh run can start.

**Secret References**: deliberately *not* implemented as a generic
``context.secrets`` lookup available to every step type — templating a
raw secret value into, say, a Notification step's message would leak
it out of the system (an exfiltration path via workflow definitions any
``workflows:write`` holder could author). The only step that ever
touches a real secret is
:class:`~cerebrum.application.workflows.step_executors.ConnectorActionStepExecutor`,
which resolves credentials internally through
cerebrum.application.connectors.connector_service.ConnectorService.get_credentials
and never surfaces the raw value back into the execution context.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from cerebrum.application.auth.audit_service import AuditService
from cerebrum.application.workflows.events import (
    StepCompletedEvent,
    StepStartedEvent,
    WorkflowCompletedEvent,
    WorkflowFailedEvent,
    WorkflowStartedEvent,
)
from cerebrum.application.workflows.step_executors import (
    StepExecutionError,
    StepExecutor,
)
from cerebrum.application.workflows.template import (
    ExecutionContext,
    evaluate_condition,
    resolve_value,
)
from cerebrum.application.workflows.workflow_service import WorkflowService
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.audit import AuditEventType
from cerebrum.infrastructure.database.models.workflow import Workflow, WorkflowStatus
from cerebrum.infrastructure.database.models.workflow_run import (
    WorkflowRun,
    WorkflowRunStatus,
)
from cerebrum.infrastructure.database.models.workflow_step_run import (
    WorkflowStepRun,
    WorkflowStepRunStatus,
)
from cerebrum.infrastructure.database.models.workflow_version import (
    StepType,
    TriggerType,
)
from cerebrum.repositories.contracts import Page, Pagination
from cerebrum.repositories.postgres.workflow_run_repository import WorkflowRunRepository
from cerebrum.repositories.postgres.workflow_step_run_repository import (
    WorkflowStepRunRepository,
)
from cerebrum.repositories.postgres.workflow_version_repository import (
    WorkflowVersionRepository,
)
from cerebrum.shared.errors.exceptions import NotFoundException, ValidationException
from cerebrum.utils.clock import utcnow

_MAX_DELAY_SECONDS = 30.0
_DEFAULT_STEP_TIMEOUT_SECONDS = 30.0
_MAX_STEP_TIMEOUT_SECONDS = 120.0
_DEFAULT_RETRY_BACKOFF_SECONDS = 1.0
_MAX_RETRY_BACKOFF_SECONDS = 10.0
_MAX_RETRY_ATTEMPTS = 5
_DISPATCH_PAGE_SIZE = 200


class _StepFailure(Exception):
    """Internal control-flow signal: a step (or an aggregate of a
    ``parallel`` step's branches) failed and the run should stop —
    caught only inside :meth:`WorkflowRunService.execute`.
    """


class WorkflowRunService:
    def __init__(
        self,
        *,
        workflow_service: WorkflowService,
        workflow_version_repository: WorkflowVersionRepository,
        workflow_run_repository: WorkflowRunRepository,
        workflow_step_run_repository: WorkflowStepRunRepository,
        step_executors: dict[StepType, StepExecutor],
        event_dispatcher: EventDispatcher,
        audit_service: AuditService,
    ) -> None:
        self._workflows = workflow_service
        self._versions = workflow_version_repository
        self._runs = workflow_run_repository
        self._step_runs = workflow_step_run_repository
        self._executors = step_executors
        self._events = event_dispatcher
        self._audit = audit_service

    async def execute(
        self,
        workflow_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        triggered_by: uuid.UUID | None,
        trigger_type: TriggerType | str = TriggerType.MANUAL,
        trigger_context: dict[str, Any] | None = None,
        initial_variables: dict[str, Any] | None = None,
    ) -> WorkflowRun:
        workflow = await self._workflows.get(workflow_id, workspace_id=workspace_id)
        if workflow.status in (
            WorkflowStatus.PAUSED.value,
            WorkflowStatus.ARCHIVED.value,
        ):
            raise ValidationException(
                f"Workflow {workflow_id} is {workflow.status} and cannot run."
            )
        version = await self._workflows.get_current_version(workflow)

        trigger_type_value = (
            trigger_type.value
            if isinstance(trigger_type, TriggerType)
            else trigger_type
        )
        trigger_context = trigger_context or {}

        run = await self._runs.add(
            WorkflowRun(
                workflow_id=workflow.id,
                workflow_version_id=version.id,
                workspace_id=workspace_id,
                organization_id=workflow.organization_id,
                status=WorkflowRunStatus.RUNNING.value,
                trigger_type=trigger_type_value,
                trigger_context=trigger_context,
                started_at=utcnow(),
                triggered_by=triggered_by,
            )
        )
        self._events.publish(
            WorkflowStartedEvent(
                workflow_id=workflow.id,
                workspace_id=workspace_id,
                run_id=run.id,
                trigger_type=trigger_type_value,
            )
        )
        await self._audit.record(
            AuditEventType.WORKFLOW_RUN_STARTED,
            user_id=triggered_by,
            workspace_id=workspace_id,
            metadata={"workflow_id": str(workflow.id), "run_id": str(run.id)},
        )

        context = ExecutionContext(
            trigger=trigger_context, variables=dict(initial_variables or {})
        )
        return await self._finish_run(
            run,
            version.steps,
            workflow=workflow,
            triggered_by=triggered_by,
            context=context,
        )

    async def retry_run(
        self,
        run_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        triggered_by: uuid.UUID | None,
    ) -> WorkflowRun:
        """CIS Phase 5 Prompt 2's Retry Failed Workflows: starts a fresh
        run pinned to the *same*
        :class:`~cerebrum.infrastructure.database.models.workflow_version.WorkflowVersion`
        the failed run used, seeding variables/step-outputs from where
        it left off and skipping only the *top-level* steps that
        already completed. Steps nested inside a ``parallel``/
        ``condition`` branch are always re-run in full — partial-branch
        completion is not tracked at that granularity, an honest,
        scoped simplification (the same kind
        cerebrum.infrastructure.connectors.azure_devops_connector's
        single-page-pagination docstring makes elsewhere in this
        codebase).
        """
        failed_run = await self._runs.get_by_id(run_id)
        if failed_run is None or failed_run.workspace_id != workspace_id:
            raise NotFoundException(f"No workflow run with id {run_id}.")
        if failed_run.status != WorkflowRunStatus.FAILED.value:
            raise ValidationException("Only a failed workflow run can be retried.")

        workflow = await self._workflows.get(
            failed_run.workflow_id, workspace_id=workspace_id
        )
        version = await self._versions.get_by_id(failed_run.workflow_version_id)
        if version is None:
            raise ValidationException(
                f"Workflow run {run_id}'s version no longer exists."
            )

        completed_step_ids = {
            step_run.step_id
            for step_run in await self._step_runs.list_by_run(failed_run.id)
            if step_run.status == WorkflowStepRunStatus.COMPLETED.value
        }
        remaining_steps = [
            step for step in version.steps if step.get("id") not in completed_step_ids
        ]

        run = await self._runs.add(
            WorkflowRun(
                workflow_id=workflow.id,
                workflow_version_id=version.id,
                workspace_id=workspace_id,
                organization_id=workflow.organization_id,
                status=WorkflowRunStatus.RUNNING.value,
                trigger_type=failed_run.trigger_type,
                trigger_context=failed_run.trigger_context,
                started_at=utcnow(),
                triggered_by=triggered_by,
            )
        )
        self._events.publish(
            WorkflowStartedEvent(
                workflow_id=workflow.id,
                workspace_id=workspace_id,
                run_id=run.id,
                trigger_type=run.trigger_type,
            )
        )
        await self._audit.record(
            AuditEventType.WORKFLOW_RUN_STARTED,
            user_id=triggered_by,
            workspace_id=workspace_id,
            metadata={
                "workflow_id": str(workflow.id),
                "run_id": str(run.id),
                "retry_of": str(failed_run.id),
            },
        )

        context = ExecutionContext(
            trigger=failed_run.trigger_context, variables=dict(failed_run.variables)
        )
        return await self._finish_run(
            run,
            remaining_steps,
            workflow=workflow,
            triggered_by=triggered_by,
            context=context,
        )

    async def dispatch_event(
        self,
        event_type: str,
        *,
        workspace_id: uuid.UUID,
        triggered_by: uuid.UUID | None = None,
        payload: dict[str, Any] | None = None,
    ) -> list[WorkflowRun]:
        """CIS Phase 5 Prompt 2's Connector Sync Completed/Document
        Uploaded/Knowledge Updated/Custom Event triggers: starts a run
        for every :attr:`~WorkflowStatus.ACTIVE` workflow in
        ``workspace_id`` whose current version's ``trigger_type``
        matches ``event_type``. A callable/API-invokable dispatch, not
        a live subscription —
        cerebrum.events.dispatcher.EventDispatcher's handlers are
        synchronous, and firing a workflow run requires awaiting real
        database/service I/O, so nothing in this codebase automatically
        calls this method when e.g. a connector sync actually
        completes; an operator, a future async-capable event bus
        adapter, or a one-line addition to the emitting service can.
        Scans one page of up to
        :data:`_DISPATCH_PAGE_SIZE` active workflows in the workspace —
        a workspace with more active workflows than that would need a
        dedicated trigger-type-indexed query, not implemented at this
        milestone.
        """
        payload = payload or {}
        page = await self._workflows.list_in_workspace(
            workspace_id=workspace_id,
            pagination=Pagination(page=1, page_size=_DISPATCH_PAGE_SIZE),
            status=WorkflowStatus.ACTIVE,
        )
        runs: list[WorkflowRun] = []
        for workflow in page.items:
            version = await self._workflows.get_current_version(workflow)
            if version.trigger_type != event_type:
                continue
            runs.append(
                await self.execute(
                    workflow.id,
                    workspace_id=workspace_id,
                    triggered_by=triggered_by,
                    trigger_type=version.trigger_type,
                    trigger_context=payload,
                )
            )
        return runs

    async def cancel(
        self, run_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> WorkflowRun:
        """See this module's docstring: moves a ``RUNNING`` run
        straight to ``CANCELLED`` — its real purpose is clearing a run
        stuck ``RUNNING`` after a crashed process.
        """
        run = await self.get_run(run_id, workspace_id=workspace_id)
        if run.status != WorkflowRunStatus.RUNNING.value:
            raise ValidationException("Only a running workflow run can be cancelled.")
        run.status = WorkflowRunStatus.CANCELLED.value
        run.cancellation_requested = True
        run.completed_at = utcnow()
        await self._runs.update(run)
        await self._audit.record(
            AuditEventType.WORKFLOW_RUN_CANCELLED,
            workspace_id=workspace_id,
            metadata={"workflow_id": str(run.workflow_id), "run_id": str(run.id)},
        )
        return run

    async def get_run(
        self, run_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> WorkflowRun:
        run = await self._runs.get_by_id(run_id)
        if run is None or run.workspace_id != workspace_id:
            raise NotFoundException(f"No workflow run with id {run_id}.")
        return run

    async def list_runs(
        self, workflow_id: uuid.UUID, *, workspace_id: uuid.UUID, pagination: Pagination
    ) -> Page[WorkflowRun]:
        await self._workflows.get(workflow_id, workspace_id=workspace_id)
        return await self._runs.list_by_workflow(workflow_id, pagination=pagination)

    async def list_step_runs(
        self, run_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> list[WorkflowStepRun]:
        run = await self.get_run(run_id, workspace_id=workspace_id)
        return await self._step_runs.list_by_run(run.id)

    # --- internals --------------------------------------------------------

    async def _finish_run(
        self,
        run: WorkflowRun,
        steps: list[dict[str, Any]],
        *,
        workflow: Workflow,
        triggered_by: uuid.UUID | None,
        context: ExecutionContext,
    ) -> WorkflowRun:
        try:
            await self._run_steps(
                steps,
                run=run,
                workflow=workflow,
                triggered_by=triggered_by,
                context=context,
            )
        except _StepFailure as exc:
            run.status = WorkflowRunStatus.FAILED.value
            run.error_message = str(exc)
            run.variables = context.variables
            run.completed_at = utcnow()
            await self._runs.update(run)
            self._events.publish(
                WorkflowFailedEvent(
                    workflow_id=workflow.id,
                    workspace_id=run.workspace_id,
                    run_id=run.id,
                    error_message=str(exc),
                )
            )
            await self._audit.record(
                AuditEventType.WORKFLOW_RUN_FAILED,
                user_id=triggered_by,
                workspace_id=run.workspace_id,
                metadata={
                    "workflow_id": str(workflow.id),
                    "run_id": str(run.id),
                    "reason": str(exc),
                },
            )
            return run

        run.status = WorkflowRunStatus.COMPLETED.value
        run.variables = context.variables
        run.completed_at = utcnow()
        await self._runs.update(run)
        self._events.publish(
            WorkflowCompletedEvent(
                workflow_id=workflow.id, workspace_id=run.workspace_id, run_id=run.id
            )
        )
        await self._audit.record(
            AuditEventType.WORKFLOW_RUN_COMPLETED,
            user_id=triggered_by,
            workspace_id=run.workspace_id,
            metadata={"workflow_id": str(workflow.id), "run_id": str(run.id)},
        )
        return run

    async def _run_steps(
        self,
        steps: list[dict[str, Any]],
        *,
        run: WorkflowRun,
        workflow: Workflow,
        triggered_by: uuid.UUID | None,
        context: ExecutionContext,
    ) -> None:
        for step in steps:
            await self._execute_step(
                step,
                run=run,
                workflow=workflow,
                triggered_by=triggered_by,
                context=context,
            )

    async def _execute_step(
        self,
        step: dict[str, Any],
        *,
        run: WorkflowRun,
        workflow: Workflow,
        triggered_by: uuid.UUID | None,
        context: ExecutionContext,
    ) -> None:
        step_id = str(step["id"])
        step_type = StepType(step["type"])
        config = step.get("config", {})

        if step_type is StepType.CONDITION:
            await self._execute_condition(
                step_id,
                config,
                run=run,
                workflow=workflow,
                triggered_by=triggered_by,
                context=context,
            )
            return
        if step_type is StepType.DELAY:
            await self._execute_delay(step_id, config, run=run, context=context)
            return
        if step_type is StepType.PARALLEL:
            await self._execute_parallel(
                step_id,
                config,
                run=run,
                workflow=workflow,
                triggered_by=triggered_by,
                context=context,
            )
            return

        await self._execute_leaf_step(
            step, run=run, workflow=workflow, triggered_by=triggered_by, context=context
        )

    async def _execute_leaf_step(
        self,
        step: dict[str, Any],
        *,
        run: WorkflowRun,
        workflow: Workflow,
        triggered_by: uuid.UUID | None,
        context: ExecutionContext,
    ) -> None:
        step_id = str(step["id"])
        step_type = StepType(step["type"])
        config = step.get("config", {})

        executor = self._executors.get(step_type)
        if executor is None:
            raise _StepFailure(
                f"No executor registered for step type '{step_type.value}'."
            )

        step_run = await self._begin_step_run(
            run, step_id=step_id, step_type=step_type.value
        )
        self._events.publish(
            StepStartedEvent(
                workflow_id=workflow.id,
                workspace_id=run.workspace_id,
                run_id=run.id,
                step_id=step_id,
                step_type=step_type.value,
            )
        )

        retry_config = step.get("retry") or {}
        max_attempts = max(
            1, min(int(retry_config.get("max_attempts", 1)), _MAX_RETRY_ATTEMPTS)
        )
        backoff_seconds = max(
            0.0,
            min(
                float(
                    retry_config.get("backoff_seconds", _DEFAULT_RETRY_BACKOFF_SECONDS)
                ),
                _MAX_RETRY_BACKOFF_SECONDS,
            ),
        )
        timeout_seconds = max(
            1.0,
            min(
                float(step.get("timeout_seconds", _DEFAULT_STEP_TIMEOUT_SECONDS)),
                _MAX_STEP_TIMEOUT_SECONDS,
            ),
        )

        last_error: str | None = None
        outcome = None
        for attempt in range(1, max_attempts + 1):
            step_run.attempt = attempt
            try:
                outcome = await asyncio.wait_for(
                    executor.execute(
                        config,
                        workspace_id=run.workspace_id,
                        triggered_by=triggered_by,
                        context=context,
                    ),
                    timeout=timeout_seconds,
                )
                last_error = None
                break
            except StepExecutionError as exc:
                last_error = str(exc)
            except TimeoutError:
                last_error = f"Step '{step_id}' timed out after {timeout_seconds}s."
            if attempt < max_attempts and backoff_seconds > 0:
                await asyncio.sleep(backoff_seconds)

        if outcome is None:
            await self._finish_step_run(
                step_run, status=WorkflowStepRunStatus.FAILED, error_message=last_error
            )
            self._events.publish(
                StepCompletedEvent(
                    workflow_id=workflow.id,
                    workspace_id=run.workspace_id,
                    run_id=run.id,
                    step_id=step_id,
                    step_type=step_type.value,
                    status=WorkflowStepRunStatus.FAILED.value,
                )
            )
            if step.get("on_failure") == "continue":
                return
            raise _StepFailure(last_error or f"Step '{step_id}' failed.")

        context.steps[step_id] = outcome.output
        output_variable = step.get("output_variable")
        if output_variable:
            context.variables[str(output_variable)] = outcome.output
        await self._finish_step_run(
            step_run, status=WorkflowStepRunStatus.COMPLETED, output=outcome.output
        )
        self._events.publish(
            StepCompletedEvent(
                workflow_id=workflow.id,
                workspace_id=run.workspace_id,
                run_id=run.id,
                step_id=step_id,
                step_type=step_type.value,
                status=WorkflowStepRunStatus.COMPLETED.value,
            )
        )

    async def _execute_condition(
        self,
        step_id: str,
        config: dict[str, Any],
        *,
        run: WorkflowRun,
        workflow: Workflow,
        triggered_by: uuid.UUID | None,
        context: ExecutionContext,
    ) -> None:
        step_run = await self._begin_step_run(
            run, step_id=step_id, step_type=StepType.CONDITION.value
        )
        branch_taken = evaluate_condition(config.get("condition", {}), context)
        nested_steps = (
            config.get("then", []) if branch_taken else config.get("else", [])
        )
        await self._finish_step_run(
            step_run,
            status=WorkflowStepRunStatus.COMPLETED,
            output={"branch": "then" if branch_taken else "else"},
        )
        if nested_steps:
            await self._run_steps(
                nested_steps,
                run=run,
                workflow=workflow,
                triggered_by=triggered_by,
                context=context,
            )

    async def _execute_delay(
        self,
        step_id: str,
        config: dict[str, Any],
        *,
        run: WorkflowRun,
        context: ExecutionContext,
    ) -> None:
        step_run = await self._begin_step_run(
            run, step_id=step_id, step_type=StepType.DELAY.value
        )
        resolved = resolve_value(config, context)
        seconds = max(0.0, min(float(resolved.get("seconds", 0)), _MAX_DELAY_SECONDS))
        await asyncio.sleep(seconds)
        await self._finish_step_run(
            step_run,
            status=WorkflowStepRunStatus.COMPLETED,
            output={"seconds": seconds},
        )

    async def _execute_parallel(
        self,
        step_id: str,
        config: dict[str, Any],
        *,
        run: WorkflowRun,
        workflow: Workflow,
        triggered_by: uuid.UUID | None,
        context: ExecutionContext,
    ) -> None:
        step_run = await self._begin_step_run(
            run, step_id=step_id, step_type=StepType.PARALLEL.value
        )
        branches = config.get("steps", [])
        failures: list[str] = []
        for branch in branches:
            try:
                await self._execute_step(
                    branch,
                    run=run,
                    workflow=workflow,
                    triggered_by=triggered_by,
                    context=context,
                )
            except _StepFailure as exc:
                failures.append(str(exc))

        status = (
            WorkflowStepRunStatus.FAILED
            if failures
            else WorkflowStepRunStatus.COMPLETED
        )
        await self._finish_step_run(
            step_run,
            status=status,
            output={"branch_count": len(branches), "failed_count": len(failures)},
        )
        if failures:
            raise _StepFailure("; ".join(failures))

    async def _begin_step_run(
        self, run: WorkflowRun, *, step_id: str, step_type: str
    ) -> WorkflowStepRun:
        return await self._step_runs.add(
            WorkflowStepRun(
                workflow_run_id=run.id,
                step_id=step_id,
                step_type=step_type,
                status=WorkflowStepRunStatus.RUNNING.value,
                attempt=1,
                started_at=utcnow(),
            )
        )

    async def _finish_step_run(
        self,
        step_run: WorkflowStepRun,
        *,
        status: WorkflowStepRunStatus,
        output: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> WorkflowStepRun:
        step_run.status = status.value
        step_run.completed_at = utcnow()
        if step_run.started_at is not None:
            elapsed = step_run.completed_at - step_run.started_at
            step_run.duration_ms = int(elapsed.total_seconds() * 1000)
        if output is not None:
            step_run.output = output
        if error_message is not None:
            step_run.error_message = error_message
        return await self._step_runs.update(step_run)
