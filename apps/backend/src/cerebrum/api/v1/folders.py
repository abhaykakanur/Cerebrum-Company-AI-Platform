"""The Folder API surface — CIS Phase 2 Prompt 1's Folder System. Every
route is workspace-scoped (:data:`~cerebrum.dependencies.auth.WorkspaceIdDep`,
from the ``X-Workspace-ID`` header) and RBAC-gated
(``Depends(require_permission(...))``) — the same structural
tenant/workspace isolation
docs/architecture/security/multi-tenancy-guide.md and
apps/backend/tests/unit/test_tenant_isolation.py already established for
the Identity & Security platform, reused here rather than reinvented.
"""

import uuid

from fastapi import APIRouter, Depends, status

from cerebrum.api.openapi_responses import STANDARD_ERROR_RESPONSES
from cerebrum.api.response_builder import (
    build_collection_response,
    build_success_response,
)
from cerebrum.api.schemas.envelope import SuccessResponse
from cerebrum.api.schemas.knowledge import (
    FolderCreateRequest,
    FolderMoveRequest,
    FolderRenameRequest,
    FolderResponse,
)
from cerebrum.dependencies.auth import (
    CurrentUserDep,
    WorkspaceIdDep,
    require_permission,
)
from cerebrum.dependencies.knowledge import FolderServiceDep
from cerebrum.dependencies.pagination import PaginationDep, SortDep
from cerebrum.dependencies.settings import SettingsDep
from cerebrum.repositories.contracts import map_page

router = APIRouter(
    prefix="/folders", tags=["Folders"], responses=STANDARD_ERROR_RESPONSES
)


@router.get(
    "",
    response_model=SuccessResponse[list[FolderResponse]],
    dependencies=[Depends(require_permission("folders:read"))],
)
async def list_folders(
    workspace_id: WorkspaceIdDep,
    folders: FolderServiceDep,
    pagination: PaginationDep,
    sort: SortDep,
    settings: SettingsDep,
    parent_id: uuid.UUID | None = None,
) -> SuccessResponse[list[FolderResponse]]:
    page = await folders.list_in_workspace(
        workspace_id=workspace_id, parent_id=parent_id, pagination=pagination, sort=sort
    )
    return build_collection_response(
        map_page(page, FolderResponse.model_validate), settings=settings
    )


@router.post(
    "",
    response_model=SuccessResponse[FolderResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("folders:write"))],
)
async def create_folder(
    body: FolderCreateRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    folders: FolderServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[FolderResponse]:
    folder = await folders.create(
        workspace_id=workspace_id,
        parent_id=body.parent_id,
        name=body.name,
        created_by=current_user.id,
    )
    return build_success_response(
        FolderResponse.model_validate(folder), settings=settings
    )


@router.get(
    "/{folder_id}",
    response_model=SuccessResponse[FolderResponse],
    dependencies=[Depends(require_permission("folders:read"))],
)
async def get_folder(
    folder_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    folders: FolderServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[FolderResponse]:
    folder = await folders.get(folder_id, workspace_id=workspace_id)
    return build_success_response(
        FolderResponse.model_validate(folder), settings=settings
    )


@router.patch(
    "/{folder_id}",
    response_model=SuccessResponse[FolderResponse],
    dependencies=[Depends(require_permission("folders:write"))],
)
async def rename_folder(
    folder_id: uuid.UUID,
    body: FolderRenameRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    folders: FolderServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[FolderResponse]:
    folder = await folders.rename(
        folder_id, workspace_id=workspace_id, name=body.name, updated_by=current_user.id
    )
    return build_success_response(
        FolderResponse.model_validate(folder), settings=settings
    )


@router.post(
    "/{folder_id}/move",
    response_model=SuccessResponse[FolderResponse],
    dependencies=[Depends(require_permission("folders:write"))],
)
async def move_folder(
    folder_id: uuid.UUID,
    body: FolderMoveRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    folders: FolderServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[FolderResponse]:
    folder = await folders.move(
        folder_id,
        workspace_id=workspace_id,
        new_parent_id=body.new_parent_id,
        updated_by=current_user.id,
    )
    return build_success_response(
        FolderResponse.model_validate(folder), settings=settings
    )


@router.delete(
    "/{folder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("folders:delete"))],
)
async def delete_folder(
    folder_id: uuid.UUID, workspace_id: WorkspaceIdDep, folders: FolderServiceDep
) -> None:
    await folders.soft_delete(folder_id, workspace_id=workspace_id)


@router.post(
    "/{folder_id}/restore",
    response_model=SuccessResponse[FolderResponse],
    dependencies=[Depends(require_permission("folders:write"))],
)
async def restore_folder(
    folder_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    folders: FolderServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[FolderResponse]:
    folder = await folders.restore(folder_id, workspace_id=workspace_id)
    return build_success_response(
        FolderResponse.model_validate(folder), settings=settings
    )
