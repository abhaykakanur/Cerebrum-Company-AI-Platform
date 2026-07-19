"""The Workflow API surface — CIS Phase 5 Prompt 2's Workflow
Definition/Versioning/Lifecycle, Execution Engine, and Scheduler
endpoints, built entirely on
:class:`~cerebrum.application.workflows.workflow_service.WorkflowService`/
:class:`~cerebrum.application.workflows.workflow_run_service.WorkflowRunService`/
:class:`~cerebrum.application.workflows.scheduler.WorkflowScheduler`
(see cerebrum.application.workflows's package docstring).

``"workflows:write"`` gates every mutating route;
``"workflows:read"`` gates read-only routes — mirroring
cerebrum.api.v1.connectors's identical read/write permission split.
Tenant/Workspace Isolation is inherited structurally: every route
resolves ``workspace_id`` from ``WorkspaceIdDep`` and every service call
is scoped by it.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from cerebrum.api.openapi_responses import STANDARD_ERROR_RESPONSES
from cerebrum.api.response_builder import (
    build_collection_response,
    build_success_response,
)
from cerebrum.api.schemas.envelope import SuccessResponse
from cerebrum.api.schemas.workflow import (
    CreateFromTemplateRequest,
    CreateScheduleRequest,
    CreateWorkflowRequest,
    ExecuteWorkflowRequest,
    UpdateWorkflowRequest,
    WorkflowResponse,
    WorkflowRunResponse,
    WorkflowScheduleResponse,
    WorkflowStepRunResponse,
    WorkflowVersionResponse,
)
from cerebrum.dependencies.auth import (
    CurrentUserDep,
    WorkspaceIdDep,
    require_permission,
)
from cerebrum.dependencies.settings import SettingsDep
from cerebrum.dependencies.workflows import (
    WorkflowRunServiceDep,
    WorkflowSchedulerDep,
    WorkflowServiceDep,
)
from cerebrum.infrastructure.database.models.workflow import WorkflowStatus
from cerebrum.repositories.contracts import Pagination, map_page

router = APIRouter(
    prefix="/workflows", tags=["Workflows"], responses=STANDARD_ERROR_RESPONSES
)

_write = Depends(require_permission("workflows:write"))
_read = Depends(require_permission("workflows:read"))


@router.post(
    "",
    response_model=SuccessResponse[WorkflowResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[_write],
)
async def create_workflow(
    body: CreateWorkflowRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    workflows: WorkflowServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[WorkflowResponse]:
    workflow = await workflows.create(
        workspace_id=workspace_id,
        organization_id=current_user.organization_id,
        name=body.name,
        description=body.description,
        trigger_type=body.trigger_type,
        trigger_config=body.trigger_config,
        steps=body.steps,
        created_by=current_user.id,
        metadata=body.workflow_metadata,
        is_template=body.is_template,
    )
    return build_success_response(
        WorkflowResponse.model_validate(workflow), settings=settings
    )


@router.get(
    "", response_model=SuccessResponse[list[WorkflowResponse]], dependencies=[_read]
)
async def list_workflows(
    workspace_id: WorkspaceIdDep,
    workflows: WorkflowServiceDep,
    settings: SettingsDep,
    workflow_status: Annotated[WorkflowStatus | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> SuccessResponse[list[WorkflowResponse]]:
    page_result = await workflows.list_in_workspace(
        workspace_id=workspace_id,
        pagination=Pagination(page=page, page_size=page_size),
        status=workflow_status,
    )
    return build_collection_response(
        map_page(page_result, WorkflowResponse.model_validate), settings=settings
    )


@router.get(
    "/templates",
    response_model=SuccessResponse[list[WorkflowResponse]],
    dependencies=[_read],
)
async def list_workflow_templates(
    workspace_id: WorkspaceIdDep,
    workflows: WorkflowServiceDep,
    settings: SettingsDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> SuccessResponse[list[WorkflowResponse]]:
    page_result = await workflows.list_templates(
        workspace_id=workspace_id, pagination=Pagination(page=page, page_size=page_size)
    )
    return build_collection_response(
        map_page(page_result, WorkflowResponse.model_validate), settings=settings
    )


@router.post(
    "/templates/{template_id}/instantiate",
    response_model=SuccessResponse[WorkflowResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[_write],
)
async def instantiate_workflow_template(
    template_id: uuid.UUID,
    body: CreateFromTemplateRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    workflows: WorkflowServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[WorkflowResponse]:
    workflow = await workflows.create_from_template(
        template_id,
        workspace_id=workspace_id,
        organization_id=current_user.organization_id,
        name=body.name,
        created_by=current_user.id,
    )
    return build_success_response(
        WorkflowResponse.model_validate(workflow), settings=settings
    )


@router.get(
    "/{workflow_id}",
    response_model=SuccessResponse[WorkflowResponse],
    dependencies=[_read],
)
async def get_workflow(
    workflow_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    workflows: WorkflowServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[WorkflowResponse]:
    workflow = await workflows.get(workflow_id, workspace_id=workspace_id)
    return build_success_response(
        WorkflowResponse.model_validate(workflow), settings=settings
    )


@router.patch(
    "/{workflow_id}",
    response_model=SuccessResponse[WorkflowResponse],
    dependencies=[_write],
)
async def update_workflow(
    workflow_id: uuid.UUID,
    body: UpdateWorkflowRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    workflows: WorkflowServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[WorkflowResponse]:
    workflow = await workflows.update_definition(
        workflow_id,
        workspace_id=workspace_id,
        updated_by=current_user.id,
        name=body.name,
        description=body.description,
        trigger_type=body.trigger_type,
        trigger_config=body.trigger_config,
        steps=body.steps,
        metadata=body.workflow_metadata,
    )
    return build_success_response(
        WorkflowResponse.model_validate(workflow), settings=settings
    )


@router.delete(
    "/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_write]
)
async def delete_workflow(
    workflow_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    workflows: WorkflowServiceDep,
) -> None:
    await workflows.delete(
        workflow_id, workspace_id=workspace_id, deleted_by=current_user.id
    )


@router.post(
    "/{workflow_id}/pause",
    response_model=SuccessResponse[WorkflowResponse],
    dependencies=[_write],
)
async def pause_workflow(
    workflow_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    workflows: WorkflowServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[WorkflowResponse]:
    workflow = await workflows.change_status(
        workflow_id,
        workspace_id=workspace_id,
        status=WorkflowStatus.PAUSED,
        updated_by=current_user.id,
    )
    return build_success_response(
        WorkflowResponse.model_validate(workflow), settings=settings
    )


@router.post(
    "/{workflow_id}/resume",
    response_model=SuccessResponse[WorkflowResponse],
    dependencies=[_write],
)
async def resume_workflow(
    workflow_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    workflows: WorkflowServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[WorkflowResponse]:
    workflow = await workflows.change_status(
        workflow_id,
        workspace_id=workspace_id,
        status=WorkflowStatus.ACTIVE,
        updated_by=current_user.id,
    )
    return build_success_response(
        WorkflowResponse.model_validate(workflow), settings=settings
    )


@router.get(
    "/{workflow_id}/versions",
    response_model=SuccessResponse[list[WorkflowVersionResponse]],
    dependencies=[_read],
)
async def list_workflow_versions(
    workflow_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    workflows: WorkflowServiceDep,
    settings: SettingsDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> SuccessResponse[list[WorkflowVersionResponse]]:
    page_result = await workflows.list_versions(
        workflow_id,
        workspace_id=workspace_id,
        pagination=Pagination(page=page, page_size=page_size),
    )
    return build_collection_response(
        map_page(page_result, WorkflowVersionResponse.model_validate), settings=settings
    )


@router.post(
    "/{workflow_id}/execute",
    response_model=SuccessResponse[WorkflowRunResponse],
    dependencies=[_write],
)
async def execute_workflow(
    workflow_id: uuid.UUID,
    body: ExecuteWorkflowRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    run_service: WorkflowRunServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[WorkflowRunResponse]:
    run = await run_service.execute(
        workflow_id,
        workspace_id=workspace_id,
        triggered_by=current_user.id,
        trigger_context=body.trigger_context,
        initial_variables=body.variables,
    )
    return build_success_response(
        WorkflowRunResponse.model_validate(run), settings=settings
    )


@router.get(
    "/{workflow_id}/runs",
    response_model=SuccessResponse[list[WorkflowRunResponse]],
    dependencies=[_read],
)
async def list_workflow_runs(
    workflow_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    run_service: WorkflowRunServiceDep,
    settings: SettingsDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> SuccessResponse[list[WorkflowRunResponse]]:
    page_result = await run_service.list_runs(
        workflow_id,
        workspace_id=workspace_id,
        pagination=Pagination(page=page, page_size=page_size),
    )
    return build_collection_response(
        map_page(page_result, WorkflowRunResponse.model_validate), settings=settings
    )


@router.get(
    "/{workflow_id}/runs/{run_id}",
    response_model=SuccessResponse[WorkflowRunResponse],
    dependencies=[_read],
)
async def get_workflow_run(
    workflow_id: uuid.UUID,
    run_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    run_service: WorkflowRunServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[WorkflowRunResponse]:
    run = await run_service.get_run(run_id, workspace_id=workspace_id)
    return build_success_response(
        WorkflowRunResponse.model_validate(run), settings=settings
    )


@router.get(
    "/{workflow_id}/runs/{run_id}/steps",
    response_model=SuccessResponse[list[WorkflowStepRunResponse]],
    dependencies=[_read],
)
async def list_workflow_run_steps(
    workflow_id: uuid.UUID,
    run_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    run_service: WorkflowRunServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[list[WorkflowStepRunResponse]]:
    step_runs = await run_service.list_step_runs(run_id, workspace_id=workspace_id)
    return build_success_response(
        [WorkflowStepRunResponse.model_validate(step_run) for step_run in step_runs],
        settings=settings,
    )


@router.post(
    "/{workflow_id}/runs/{run_id}/cancel",
    response_model=SuccessResponse[WorkflowRunResponse],
    dependencies=[_write],
)
async def cancel_workflow_run(
    workflow_id: uuid.UUID,
    run_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    run_service: WorkflowRunServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[WorkflowRunResponse]:
    run = await run_service.cancel(run_id, workspace_id=workspace_id)
    return build_success_response(
        WorkflowRunResponse.model_validate(run), settings=settings
    )


@router.post(
    "/{workflow_id}/runs/{run_id}/retry",
    response_model=SuccessResponse[WorkflowRunResponse],
    dependencies=[_write],
)
async def retry_workflow_run(
    workflow_id: uuid.UUID,
    run_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    run_service: WorkflowRunServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[WorkflowRunResponse]:
    run = await run_service.retry_run(
        run_id, workspace_id=workspace_id, triggered_by=current_user.id
    )
    return build_success_response(
        WorkflowRunResponse.model_validate(run), settings=settings
    )


@router.post(
    "/{workflow_id}/schedules",
    response_model=SuccessResponse[WorkflowScheduleResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[_write],
)
async def create_workflow_schedule(
    workflow_id: uuid.UUID,
    body: CreateScheduleRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    scheduler: WorkflowSchedulerDep,
    settings: SettingsDep,
) -> SuccessResponse[WorkflowScheduleResponse]:
    schedule = await scheduler.create_schedule(
        workflow_id,
        workspace_id=workspace_id,
        schedule_type=body.schedule_type,
        cron_expression=body.cron_expression,
        run_at=body.run_at,
        created_by=current_user.id,
    )
    return build_success_response(
        WorkflowScheduleResponse.model_validate(schedule), settings=settings
    )


@router.get(
    "/{workflow_id}/schedules",
    response_model=SuccessResponse[list[WorkflowScheduleResponse]],
    dependencies=[_read],
)
async def list_workflow_schedules(
    workflow_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    scheduler: WorkflowSchedulerDep,
    settings: SettingsDep,
) -> SuccessResponse[list[WorkflowScheduleResponse]]:
    schedules = await scheduler.list_schedules(workflow_id, workspace_id=workspace_id)
    return build_success_response(
        [WorkflowScheduleResponse.model_validate(schedule) for schedule in schedules],
        settings=settings,
    )


@router.delete(
    "/{workflow_id}/schedules/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_write],
)
async def delete_workflow_schedule(
    workflow_id: uuid.UUID,
    schedule_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    scheduler: WorkflowSchedulerDep,
) -> None:
    await scheduler.delete_schedule(
        schedule_id, workspace_id=workspace_id, deleted_by=current_user.id
    )
