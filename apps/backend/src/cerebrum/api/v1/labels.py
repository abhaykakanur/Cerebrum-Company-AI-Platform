"""The Label API surface — see cerebrum.api.v1.tags's docstring;
identical shape, distinct taxonomy/permission codes.
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
    LabelCreateRequest,
    LabelResponse,
    LabelUpdateRequest,
)
from cerebrum.dependencies.auth import WorkspaceIdDep, require_permission
from cerebrum.dependencies.knowledge import LabelServiceDep
from cerebrum.dependencies.pagination import PaginationDep, SortDep
from cerebrum.dependencies.settings import SettingsDep
from cerebrum.repositories.contracts import map_page

router = APIRouter(
    prefix="/labels", tags=["Labels"], responses=STANDARD_ERROR_RESPONSES
)


@router.get(
    "",
    response_model=SuccessResponse[list[LabelResponse]],
    dependencies=[Depends(require_permission("labels:read"))],
)
async def list_labels(
    workspace_id: WorkspaceIdDep,
    labels: LabelServiceDep,
    pagination: PaginationDep,
    sort: SortDep,
    settings: SettingsDep,
) -> SuccessResponse[list[LabelResponse]]:
    page = await labels.list_in_workspace(
        workspace_id=workspace_id, pagination=pagination, sort=sort
    )
    return build_collection_response(
        map_page(page, LabelResponse.model_validate), settings=settings
    )


@router.post(
    "",
    response_model=SuccessResponse[LabelResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("labels:write"))],
)
async def create_label(
    body: LabelCreateRequest,
    workspace_id: WorkspaceIdDep,
    labels: LabelServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[LabelResponse]:
    label = await labels.create(
        workspace_id=workspace_id, name=body.name, color=body.color
    )
    return build_success_response(
        LabelResponse.model_validate(label), settings=settings
    )


@router.get(
    "/{label_id}",
    response_model=SuccessResponse[LabelResponse],
    dependencies=[Depends(require_permission("labels:read"))],
)
async def get_label(
    label_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    labels: LabelServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[LabelResponse]:
    label = await labels.get(label_id, workspace_id=workspace_id)
    return build_success_response(
        LabelResponse.model_validate(label), settings=settings
    )


@router.patch(
    "/{label_id}",
    response_model=SuccessResponse[LabelResponse],
    dependencies=[Depends(require_permission("labels:write"))],
)
async def rename_label(
    label_id: uuid.UUID,
    body: LabelUpdateRequest,
    workspace_id: WorkspaceIdDep,
    labels: LabelServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[LabelResponse]:
    label = await labels.rename(
        label_id, workspace_id=workspace_id, name=body.name, color=body.color
    )
    return build_success_response(
        LabelResponse.model_validate(label), settings=settings
    )


@router.delete(
    "/{label_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("labels:write"))],
)
async def delete_label(
    label_id: uuid.UUID, workspace_id: WorkspaceIdDep, labels: LabelServiceDep
) -> None:
    await labels.delete(label_id, workspace_id=workspace_id)
