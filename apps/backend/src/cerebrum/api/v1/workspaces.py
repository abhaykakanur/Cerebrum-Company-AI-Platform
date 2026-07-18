"""The Workspace API surface — CIS Phase 2 Prompt 1. Tenant Ownership is
structural: every route scopes through
:data:`~cerebrum.dependencies.request_context.TenantIdDep`, so a
workspace belonging to a different organization 404s rather than
leaking its existence — see
cerebrum.application.knowledge.workspace_service's docstring. Same RBAC
simplification as cerebrum.api.v1.organizations: creating/listing/
renaming a workspace is an organization-level action, not scoped to one
already-existing workspace's membership, so only authentication is
required here, not ``require_permission``.
"""

import uuid

from fastapi import APIRouter, status

from cerebrum.api.openapi_responses import STANDARD_ERROR_RESPONSES
from cerebrum.api.response_builder import (
    build_collection_response,
    build_success_response,
)
from cerebrum.api.schemas.envelope import SuccessResponse
from cerebrum.api.schemas.knowledge import (
    WorkspaceCreateRequest,
    WorkspaceResponse,
    WorkspaceUpdateRequest,
)
from cerebrum.dependencies.auth import CurrentUserDep
from cerebrum.dependencies.knowledge import WorkspaceServiceDep
from cerebrum.dependencies.pagination import PaginationDep, SortDep
from cerebrum.dependencies.request_context import TenantIdDep
from cerebrum.dependencies.settings import SettingsDep
from cerebrum.repositories.contracts import map_page

router = APIRouter(
    prefix="/workspaces", tags=["Workspaces"], responses=STANDARD_ERROR_RESPONSES
)


@router.get("", response_model=SuccessResponse[list[WorkspaceResponse]])
async def list_workspaces(
    _current_user: CurrentUserDep,
    tenant_id: TenantIdDep,
    workspaces: WorkspaceServiceDep,
    pagination: PaginationDep,
    sort: SortDep,
    settings: SettingsDep,
) -> SuccessResponse[list[WorkspaceResponse]]:
    page = await workspaces.list_for_organization(
        organization_id=tenant_id, pagination=pagination, sort=sort
    )
    return build_collection_response(
        map_page(page, WorkspaceResponse.model_validate), settings=settings
    )


@router.post(
    "",
    response_model=SuccessResponse[WorkspaceResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace(
    body: WorkspaceCreateRequest,
    _current_user: CurrentUserDep,
    tenant_id: TenantIdDep,
    workspaces: WorkspaceServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[WorkspaceResponse]:
    workspace = await workspaces.create(
        organization_id=tenant_id, name=body.name, slug=body.slug
    )
    return build_success_response(
        WorkspaceResponse.model_validate(workspace), settings=settings
    )


@router.get("/{workspace_id}", response_model=SuccessResponse[WorkspaceResponse])
async def get_workspace(
    workspace_id: uuid.UUID,
    _current_user: CurrentUserDep,
    tenant_id: TenantIdDep,
    workspaces: WorkspaceServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[WorkspaceResponse]:
    workspace = await workspaces.get(workspace_id, organization_id=tenant_id)
    return build_success_response(
        WorkspaceResponse.model_validate(workspace), settings=settings
    )


@router.patch("/{workspace_id}", response_model=SuccessResponse[WorkspaceResponse])
async def rename_workspace(
    workspace_id: uuid.UUID,
    body: WorkspaceUpdateRequest,
    _current_user: CurrentUserDep,
    tenant_id: TenantIdDep,
    workspaces: WorkspaceServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[WorkspaceResponse]:
    workspace = await workspaces.rename(
        workspace_id, organization_id=tenant_id, name=body.name
    )
    return build_success_response(
        WorkspaceResponse.model_validate(workspace), settings=settings
    )


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: uuid.UUID,
    _current_user: CurrentUserDep,
    tenant_id: TenantIdDep,
    workspaces: WorkspaceServiceDep,
) -> None:
    await workspaces.delete(workspace_id, organization_id=tenant_id)
