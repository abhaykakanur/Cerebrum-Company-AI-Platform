"""The Connector API surface — CIS Phase 5 Prompt 1's Connector
Registry, Configuration, Lifecycle, Health, and Sync Engine endpoints,
built entirely on
:class:`~cerebrum.application.connectors.connector_service.ConnectorService`/
:class:`~cerebrum.application.connectors.connector_sync_service.ConnectorSyncService`
(see cerebrum.application.connectors's package docstring).

``"connectors:write"`` gates every mutating route (register/configure/
delete/start-sync/stop-sync); ``"connectors:read"`` gates read-only
routes — mirroring cerebrum.api.v1.conversations's identical
read/write permission split. Tenant/Workspace Isolation is inherited
structurally: every route resolves ``workspace_id`` from
``WorkspaceIdDep`` and every service call is scoped by it.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from cerebrum.api.openapi_responses import STANDARD_ERROR_RESPONSES
from cerebrum.api.response_builder import (
    build_collection_response,
    build_success_response,
)
from cerebrum.api.schemas.connector import (
    ConfigureConnectorRequest,
    ConnectorResponse,
    RegisterConnectorRequest,
    StartSyncRequest,
    SyncRunResponse,
)
from cerebrum.api.schemas.envelope import SuccessResponse
from cerebrum.dependencies.auth import (
    CurrentUserDep,
    WorkspaceIdDep,
    require_permission,
)
from cerebrum.dependencies.connectors import (
    ConnectorServiceDep,
    ConnectorSyncServiceDep,
)
from cerebrum.dependencies.infrastructure import HttpClientDep
from cerebrum.dependencies.settings import SettingsDep
from cerebrum.infrastructure.database.models.connector import (
    ConnectorStatus,
    ConnectorType,
)
from cerebrum.repositories.contracts import Pagination, map_page

router = APIRouter(
    prefix="/connectors", tags=["Connectors"], responses=STANDARD_ERROR_RESPONSES
)

_write = Depends(require_permission("connectors:write"))
_read = Depends(require_permission("connectors:read"))


@router.post(
    "",
    response_model=SuccessResponse[ConnectorResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[_write],
)
async def register_connector(
    body: RegisterConnectorRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    connectors: ConnectorServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[ConnectorResponse]:
    connector = await connectors.register(
        workspace_id=workspace_id,
        organization_id=current_user.organization_id,
        connector_type=body.connector_type,
        name=body.name,
        auth_type=body.auth_type,
        credentials=body.credentials,
        config=body.config,
        created_by=current_user.id,
        sync_interval_seconds=body.sync_interval_seconds,
    )
    return build_success_response(
        ConnectorResponse.model_validate(connector), settings=settings
    )


@router.get(
    "", response_model=SuccessResponse[list[ConnectorResponse]], dependencies=[_read]
)
async def list_connectors(
    workspace_id: WorkspaceIdDep,
    connectors: ConnectorServiceDep,
    settings: SettingsDep,
    connector_status: Annotated[ConnectorStatus | None, Query()] = None,
    connector_type: Annotated[ConnectorType | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> SuccessResponse[list[ConnectorResponse]]:
    page_result = await connectors.list_in_workspace(
        workspace_id=workspace_id,
        pagination=Pagination(page=page, page_size=page_size),
        status=connector_status,
        connector_type=connector_type,
    )
    return build_collection_response(
        map_page(page_result, ConnectorResponse.model_validate), settings=settings
    )


@router.get(
    "/{connector_id}",
    response_model=SuccessResponse[ConnectorResponse],
    dependencies=[_read],
)
async def get_connector(
    connector_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    connectors: ConnectorServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[ConnectorResponse]:
    connector = await connectors.get(connector_id, workspace_id=workspace_id)
    return build_success_response(
        ConnectorResponse.model_validate(connector), settings=settings
    )


@router.patch(
    "/{connector_id}",
    response_model=SuccessResponse[ConnectorResponse],
    dependencies=[_write],
)
async def configure_connector(
    connector_id: uuid.UUID,
    body: ConfigureConnectorRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    connectors: ConnectorServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[ConnectorResponse]:
    fields_set = body.model_fields_set
    connector = await connectors.configure(
        connector_id,
        workspace_id=workspace_id,
        updated_by=current_user.id,
        name=body.name,
        config=body.config,
        credentials=body.credentials,
        sync_interval_seconds=(
            body.sync_interval_seconds if "sync_interval_seconds" in fields_set else ...
        ),
    )
    return build_success_response(
        ConnectorResponse.model_validate(connector), settings=settings
    )


@router.delete(
    "/{connector_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_write]
)
async def delete_connector(
    connector_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    connectors: ConnectorServiceDep,
) -> None:
    await connectors.delete(
        connector_id, workspace_id=workspace_id, deleted_by=current_user.id
    )


@router.get(
    "/{connector_id}/health",
    response_model=SuccessResponse[ConnectorResponse],
    dependencies=[_read],
)
async def check_connector_health(
    connector_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    connectors: ConnectorServiceDep,
    http_client: HttpClientDep,
    settings: SettingsDep,
) -> SuccessResponse[ConnectorResponse]:
    connector = await connectors.check_health(
        connector_id,
        workspace_id=workspace_id,
        http_client=http_client,
        checked_by=current_user.id,
    )
    return build_success_response(
        ConnectorResponse.model_validate(connector), settings=settings
    )


@router.post(
    "/{connector_id}/sync",
    response_model=SuccessResponse[SyncRunResponse],
    dependencies=[_write],
)
async def start_sync(
    connector_id: uuid.UUID,
    body: StartSyncRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    sync_service: ConnectorSyncServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[SyncRunResponse]:
    run = await sync_service.start_sync(
        connector_id,
        workspace_id=workspace_id,
        triggered_by=current_user.id,
        sync_type=body.sync_type,
        resume=body.resume,
    )
    return build_success_response(
        SyncRunResponse.model_validate(run), settings=settings
    )


@router.post(
    "/{connector_id}/sync/{sync_run_id}/stop",
    response_model=SuccessResponse[SyncRunResponse],
    dependencies=[_write],
)
async def stop_sync(
    connector_id: uuid.UUID,
    sync_run_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    sync_service: ConnectorSyncServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[SyncRunResponse]:
    run = await sync_service.stop_sync(
        connector_id, sync_run_id, workspace_id=workspace_id
    )
    return build_success_response(
        SyncRunResponse.model_validate(run), settings=settings
    )


@router.get(
    "/{connector_id}/sync/{sync_run_id}",
    response_model=SuccessResponse[SyncRunResponse],
    dependencies=[_read],
)
async def get_sync_status(
    connector_id: uuid.UUID,
    sync_run_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    sync_service: ConnectorSyncServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[SyncRunResponse]:
    run = await sync_service.get_run(
        connector_id, sync_run_id, workspace_id=workspace_id
    )
    return build_success_response(
        SyncRunResponse.model_validate(run), settings=settings
    )


@router.get(
    "/{connector_id}/sync-history",
    response_model=SuccessResponse[list[SyncRunResponse]],
    dependencies=[_read],
)
async def get_sync_history(
    connector_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    sync_service: ConnectorSyncServiceDep,
    settings: SettingsDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> SuccessResponse[list[SyncRunResponse]]:
    page_result = await sync_service.list_runs(
        connector_id,
        workspace_id=workspace_id,
        pagination=Pagination(page=page, page_size=page_size),
    )
    return build_collection_response(
        map_page(page_result, SyncRunResponse.model_validate), settings=settings
    )
