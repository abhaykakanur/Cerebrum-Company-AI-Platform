"""The Collection API surface — CIS Phase 2 Prompt 1's Collections,
extended with CIS Phase 2 Prompt 2's Bulk Operations
(``POST/DELETE .../documents/bulk``).
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
    BulkDocumentIdsRequest,
    BulkOperationResponse,
    CollectionCreateRequest,
    CollectionResponse,
    CollectionUpdateRequest,
)
from cerebrum.dependencies.auth import (
    CurrentUserDep,
    WorkspaceIdDep,
    require_permission,
)
from cerebrum.dependencies.knowledge import CollectionServiceDep
from cerebrum.dependencies.pagination import PaginationDep, SortDep
from cerebrum.dependencies.settings import SettingsDep
from cerebrum.repositories.contracts import map_page

router = APIRouter(
    prefix="/collections", tags=["Collections"], responses=STANDARD_ERROR_RESPONSES
)


@router.get(
    "",
    response_model=SuccessResponse[list[CollectionResponse]],
    dependencies=[Depends(require_permission("collections:read"))],
)
async def list_collections(
    workspace_id: WorkspaceIdDep,
    collections: CollectionServiceDep,
    pagination: PaginationDep,
    sort: SortDep,
    settings: SettingsDep,
) -> SuccessResponse[list[CollectionResponse]]:
    page = await collections.list_in_workspace(
        workspace_id=workspace_id, pagination=pagination, sort=sort
    )
    return build_collection_response(
        map_page(page, CollectionResponse.model_validate), settings=settings
    )


@router.post(
    "",
    response_model=SuccessResponse[CollectionResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("collections:write"))],
)
async def create_collection(
    body: CollectionCreateRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    collections: CollectionServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[CollectionResponse]:
    collection = await collections.create(
        workspace_id=workspace_id,
        name=body.name,
        description=body.description,
        created_by=current_user.id,
    )
    return build_success_response(
        CollectionResponse.model_validate(collection), settings=settings
    )


@router.get(
    "/{collection_id}",
    response_model=SuccessResponse[CollectionResponse],
    dependencies=[Depends(require_permission("collections:read"))],
)
async def get_collection(
    collection_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    collections: CollectionServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[CollectionResponse]:
    collection = await collections.get(collection_id, workspace_id=workspace_id)
    return build_success_response(
        CollectionResponse.model_validate(collection), settings=settings
    )


@router.patch(
    "/{collection_id}",
    response_model=SuccessResponse[CollectionResponse],
    dependencies=[Depends(require_permission("collections:write"))],
)
async def rename_collection(
    collection_id: uuid.UUID,
    body: CollectionUpdateRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    collections: CollectionServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[CollectionResponse]:
    collection = await collections.rename(
        collection_id,
        workspace_id=workspace_id,
        name=body.name,
        description=body.description,
        updated_by=current_user.id,
    )
    return build_success_response(
        CollectionResponse.model_validate(collection), settings=settings
    )


@router.delete(
    "/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("collections:write"))],
)
async def delete_collection(
    collection_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    collections: CollectionServiceDep,
) -> None:
    await collections.soft_delete(collection_id, workspace_id=workspace_id)


@router.post(
    "/{collection_id}/restore",
    response_model=SuccessResponse[CollectionResponse],
    dependencies=[Depends(require_permission("collections:write"))],
)
async def restore_collection(
    collection_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    collections: CollectionServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[CollectionResponse]:
    collection = await collections.restore(collection_id, workspace_id=workspace_id)
    return build_success_response(
        CollectionResponse.model_validate(collection), settings=settings
    )


@router.post(
    "/{collection_id}/documents/bulk",
    response_model=SuccessResponse[BulkOperationResponse],
    dependencies=[Depends(require_permission("collections:write"))],
)
async def add_documents_bulk(
    collection_id: uuid.UUID,
    body: BulkDocumentIdsRequest,
    workspace_id: WorkspaceIdDep,
    collections: CollectionServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[BulkOperationResponse]:
    succeeded = await collections.add_documents_bulk(
        collection_id, body.document_ids, workspace_id=workspace_id
    )
    return build_success_response(
        BulkOperationResponse(requested=len(body.document_ids), succeeded=succeeded),
        settings=settings,
    )


@router.delete(
    "/{collection_id}/documents/bulk",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("collections:write"))],
)
async def remove_documents_bulk(
    collection_id: uuid.UUID,
    body: BulkDocumentIdsRequest,
    workspace_id: WorkspaceIdDep,
    collections: CollectionServiceDep,
) -> None:
    await collections.remove_documents_bulk(
        collection_id, body.document_ids, workspace_id=workspace_id
    )


# Registered AFTER /documents/bulk above: FastAPI/Starlette matches path
# routes in registration order, and {document_id} would otherwise greedily
# capture the literal segment "bulk" as an (invalid) UUID path parameter,
# producing a 422 instead of ever reaching the bulk routes.
@router.post(
    "/{collection_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("collections:write"))],
)
async def add_document(
    collection_id: uuid.UUID,
    document_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    collections: CollectionServiceDep,
) -> None:
    await collections.add_document(
        collection_id, document_id, workspace_id=workspace_id
    )


@router.delete(
    "/{collection_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("collections:write"))],
)
async def remove_document(
    collection_id: uuid.UUID,
    document_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    collections: CollectionServiceDep,
) -> None:
    await collections.remove_document(
        collection_id, document_id, workspace_id=workspace_id
    )


@router.get(
    "/{collection_id}/documents",
    response_model=SuccessResponse[list[uuid.UUID]],
    dependencies=[Depends(require_permission("collections:read"))],
)
async def list_collection_documents(
    collection_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    collections: CollectionServiceDep,
    pagination: PaginationDep,
    settings: SettingsDep,
) -> SuccessResponse[list[uuid.UUID]]:
    page = await collections.list_documents(
        collection_id, workspace_id=workspace_id, pagination=pagination
    )
    return build_collection_response(page, settings=settings)
