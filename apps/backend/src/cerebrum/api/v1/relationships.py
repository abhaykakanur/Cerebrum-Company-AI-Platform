"""The Relationship API surface — CIS Phase 3 Prompt 1's Knowledge
Graph & Entity Intelligence: CRUD and soft delete/restore. See
cerebrum.api.v1.entities's docstring for the shared search/soft-delete-
propagation conventions this router also follows.
"""

import uuid

from fastapi import APIRouter, Depends, status

from cerebrum.api.openapi_responses import STANDARD_ERROR_RESPONSES
from cerebrum.api.response_builder import (
    build_collection_response,
    build_success_response,
)
from cerebrum.api.schemas.envelope import SuccessResponse
from cerebrum.api.schemas.knowledge_graph import (
    RelationshipCreateRequest,
    RelationshipResponse,
    RelationshipUpdateRequest,
)
from cerebrum.dependencies.auth import (
    CurrentUserDep,
    WorkspaceIdDep,
    require_permission,
)
from cerebrum.dependencies.knowledge_graph import (
    KnowledgeGraphServiceDep,
    RelationshipServiceDep,
)
from cerebrum.dependencies.pagination import FilterDep, PaginationDep, SortDep
from cerebrum.dependencies.settings import SettingsDep
from cerebrum.repositories.contracts import map_page

router = APIRouter(
    prefix="/relationships",
    tags=["Relationships"],
    responses=STANDARD_ERROR_RESPONSES,
)


@router.get(
    "",
    response_model=SuccessResponse[list[RelationshipResponse]],
    dependencies=[Depends(require_permission("relationships:read"))],
)
async def list_relationships(
    workspace_id: WorkspaceIdDep,
    relationships: RelationshipServiceDep,
    pagination: PaginationDep,
    sort: SortDep,
    filters: FilterDep,
    settings: SettingsDep,
) -> SuccessResponse[list[RelationshipResponse]]:
    page = await relationships.list_in_workspace(
        workspace_id=workspace_id, pagination=pagination, filters=filters, sort=sort
    )
    return build_collection_response(
        map_page(page, RelationshipResponse.model_validate), settings=settings
    )


@router.post(
    "",
    response_model=SuccessResponse[RelationshipResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("relationships:write"))],
)
async def create_relationship(
    body: RelationshipCreateRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    relationships: RelationshipServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[RelationshipResponse]:
    relationship = await relationships.create(
        workspace_id=workspace_id,
        organization_id=current_user.organization_id,
        source_entity_id=body.source_entity_id,
        target_entity_id=body.target_entity_id,
        relationship_type=body.relationship_type,
        custom_type_name=body.custom_type_name,
        confidence=body.confidence,
        evidence=body.evidence,
        created_by=current_user.id,
    )
    return build_success_response(
        RelationshipResponse.model_validate(relationship), settings=settings
    )


@router.get(
    "/{relationship_id}",
    response_model=SuccessResponse[RelationshipResponse],
    dependencies=[Depends(require_permission("relationships:read"))],
)
async def get_relationship(
    relationship_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    relationships: RelationshipServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[RelationshipResponse]:
    relationship = await relationships.get(relationship_id, workspace_id=workspace_id)
    return build_success_response(
        RelationshipResponse.model_validate(relationship), settings=settings
    )


@router.patch(
    "/{relationship_id}",
    response_model=SuccessResponse[RelationshipResponse],
    dependencies=[Depends(require_permission("relationships:write"))],
)
async def update_relationship(
    relationship_id: uuid.UUID,
    body: RelationshipUpdateRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    relationships: RelationshipServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[RelationshipResponse]:
    relationship = await relationships.update(
        relationship_id,
        workspace_id=workspace_id,
        confidence=body.confidence,
        evidence=body.evidence,
        updated_by=current_user.id,
    )
    return build_success_response(
        RelationshipResponse.model_validate(relationship), settings=settings
    )


@router.delete(
    "/{relationship_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("relationships:delete"))],
)
async def delete_relationship(
    relationship_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    graph: KnowledgeGraphServiceDep,
) -> None:
    await graph.soft_delete_relationship(relationship_id, workspace_id=workspace_id)


@router.post(
    "/{relationship_id}/restore",
    response_model=SuccessResponse[RelationshipResponse],
    dependencies=[Depends(require_permission("relationships:write"))],
)
async def restore_relationship(
    relationship_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    relationships: RelationshipServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[RelationshipResponse]:
    relationship = await relationships.restore(
        relationship_id, workspace_id=workspace_id
    )
    return build_success_response(
        RelationshipResponse.model_validate(relationship), settings=settings
    )
