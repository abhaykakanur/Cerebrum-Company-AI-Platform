"""The Tag API surface — CIS Phase 2 Prompt 1's Tags & Labels CRUD.
Assignment to a specific document lives on
cerebrum.api.v1.documents (``POST/DELETE /documents/{id}/tags/{tag_id}``).
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
    TagCreateRequest,
    TagResponse,
    TagUpdateRequest,
)
from cerebrum.dependencies.auth import WorkspaceIdDep, require_permission
from cerebrum.dependencies.knowledge import TagServiceDep
from cerebrum.dependencies.pagination import PaginationDep, SortDep
from cerebrum.dependencies.settings import SettingsDep
from cerebrum.repositories.contracts import map_page

router = APIRouter(prefix="/tags", tags=["Tags"], responses=STANDARD_ERROR_RESPONSES)


@router.get(
    "",
    response_model=SuccessResponse[list[TagResponse]],
    dependencies=[Depends(require_permission("tags:read"))],
)
async def list_tags(
    workspace_id: WorkspaceIdDep,
    tags: TagServiceDep,
    pagination: PaginationDep,
    sort: SortDep,
    settings: SettingsDep,
) -> SuccessResponse[list[TagResponse]]:
    page = await tags.list_in_workspace(
        workspace_id=workspace_id, pagination=pagination, sort=sort
    )
    return build_collection_response(
        map_page(page, TagResponse.model_validate), settings=settings
    )


@router.post(
    "",
    response_model=SuccessResponse[TagResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("tags:write"))],
)
async def create_tag(
    body: TagCreateRequest,
    workspace_id: WorkspaceIdDep,
    tags: TagServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[TagResponse]:
    tag = await tags.create(workspace_id=workspace_id, name=body.name)
    return build_success_response(TagResponse.model_validate(tag), settings=settings)


@router.get(
    "/{tag_id}",
    response_model=SuccessResponse[TagResponse],
    dependencies=[Depends(require_permission("tags:read"))],
)
async def get_tag(
    tag_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    tags: TagServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[TagResponse]:
    tag = await tags.get(tag_id, workspace_id=workspace_id)
    return build_success_response(TagResponse.model_validate(tag), settings=settings)


@router.patch(
    "/{tag_id}",
    response_model=SuccessResponse[TagResponse],
    dependencies=[Depends(require_permission("tags:write"))],
)
async def rename_tag(
    tag_id: uuid.UUID,
    body: TagUpdateRequest,
    workspace_id: WorkspaceIdDep,
    tags: TagServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[TagResponse]:
    tag = await tags.rename(tag_id, workspace_id=workspace_id, name=body.name)
    return build_success_response(TagResponse.model_validate(tag), settings=settings)


@router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("tags:write"))],
)
async def delete_tag(
    tag_id: uuid.UUID, workspace_id: WorkspaceIdDep, tags: TagServiceDep
) -> None:
    await tags.delete(tag_id, workspace_id=workspace_id)
