"""The Entity API surface — CIS Phase 3 Prompt 1's Knowledge Graph &
Entity Intelligence: CRUD, soft delete/restore, search (via the
standard ``?filter=`` query syntax — see
cerebrum.api.v1.documents.list_documents's identical precedent),
history, and neighbors (a real Neo4j graph query, not a PostgreSQL
join — see
cerebrum.application.knowledge_graph.knowledge_graph_service.KnowledgeGraphService.get_neighbors).
"""

import uuid

from fastapi import APIRouter, Depends, Query, status

from cerebrum.api.openapi_responses import STANDARD_ERROR_RESPONSES
from cerebrum.api.response_builder import (
    build_collection_response,
    build_success_response,
)
from cerebrum.api.schemas.envelope import SuccessResponse
from cerebrum.api.schemas.knowledge_graph import (
    EntityCreateRequest,
    EntityHistoryResponse,
    EntityResponse,
    EntityUpdateRequest,
    GraphNodeResponse,
)
from cerebrum.api.schemas.semantic import SearchHitResponse
from cerebrum.dependencies.auth import (
    CurrentUserDep,
    WorkspaceIdDep,
    require_permission,
)
from cerebrum.dependencies.knowledge_graph import (
    EntityServiceDep,
    KnowledgeGraphServiceDep,
)
from cerebrum.dependencies.pagination import FilterDep, PaginationDep, SortDep
from cerebrum.dependencies.semantic import HybridSearchServiceDep
from cerebrum.dependencies.settings import SettingsDep
from cerebrum.infrastructure.embeddings.kind import EmbeddingKind
from cerebrum.repositories.contracts import map_page

router = APIRouter(
    prefix="/entities", tags=["Entities"], responses=STANDARD_ERROR_RESPONSES
)


@router.get(
    "",
    response_model=SuccessResponse[list[EntityResponse]],
    dependencies=[Depends(require_permission("entities:read"))],
)
async def list_entities(
    workspace_id: WorkspaceIdDep,
    entities: EntityServiceDep,
    pagination: PaginationDep,
    sort: SortDep,
    filters: FilterDep,
    settings: SettingsDep,
) -> SuccessResponse[list[EntityResponse]]:
    """Entity Search: ``?filter=canonical_name:contains:acme`` — the
    same standard filter syntax every other list endpoint in this API
    already supports.
    """
    page = await entities.list_in_workspace(
        workspace_id=workspace_id, pagination=pagination, filters=filters, sort=sort
    )
    return build_collection_response(
        map_page(page, EntityResponse.model_validate), settings=settings
    )


@router.post(
    "",
    response_model=SuccessResponse[EntityResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("entities:write"))],
)
async def create_entity(
    body: EntityCreateRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    entities: EntityServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[EntityResponse]:
    entity = await entities.create(
        workspace_id=workspace_id,
        organization_id=current_user.organization_id,
        entity_type=body.entity_type,
        custom_type_name=body.custom_type_name,
        canonical_name=body.canonical_name,
        aliases=body.aliases,
        description=body.description,
        confidence=body.confidence,
        created_by=current_user.id,
    )
    return build_success_response(
        EntityResponse.model_validate(entity), settings=settings
    )


@router.get(
    "/{entity_id}",
    response_model=SuccessResponse[EntityResponse],
    dependencies=[Depends(require_permission("entities:read"))],
)
async def get_entity(
    entity_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    entities: EntityServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[EntityResponse]:
    entity = await entities.get(entity_id, workspace_id=workspace_id)
    return build_success_response(
        EntityResponse.model_validate(entity), settings=settings
    )


@router.patch(
    "/{entity_id}",
    response_model=SuccessResponse[EntityResponse],
    dependencies=[Depends(require_permission("entities:write"))],
)
async def update_entity(
    entity_id: uuid.UUID,
    body: EntityUpdateRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    entities: EntityServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[EntityResponse]:
    entity = await entities.update(
        entity_id,
        workspace_id=workspace_id,
        canonical_name=body.canonical_name,
        aliases=body.aliases,
        description=body.description,
        updated_by=current_user.id,
    )
    return build_success_response(
        EntityResponse.model_validate(entity), settings=settings
    )


@router.delete(
    "/{entity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("entities:delete"))],
)
async def delete_entity(
    entity_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    graph: KnowledgeGraphServiceDep,
) -> None:
    """Soft-deletes the PostgreSQL row and propagates the deletion into
    the Neo4j graph — CIS Phase 3 Prompt 1's Soft Delete Propagation.
    """
    await graph.soft_delete_entity(entity_id, workspace_id=workspace_id)


@router.post(
    "/{entity_id}/restore",
    response_model=SuccessResponse[EntityResponse],
    dependencies=[Depends(require_permission("entities:write"))],
)
async def restore_entity(
    entity_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    entities: EntityServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[EntityResponse]:
    entity = await entities.restore(entity_id, workspace_id=workspace_id)
    return build_success_response(
        EntityResponse.model_validate(entity), settings=settings
    )


@router.get(
    "/{entity_id}/history",
    response_model=SuccessResponse[EntityHistoryResponse],
    dependencies=[Depends(require_permission("entities:read"))],
)
async def get_entity_history(
    entity_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    entities: EntityServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[EntityHistoryResponse]:
    provenance = await entities.get_history(entity_id, workspace_id=workspace_id)
    return build_success_response(
        EntityHistoryResponse(provenance=provenance), settings=settings
    )


@router.get(
    "/{entity_id}/neighbors",
    response_model=SuccessResponse[list[GraphNodeResponse]],
    dependencies=[Depends(require_permission("entities:read"))],
)
async def get_entity_neighbors(
    entity_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    graph: KnowledgeGraphServiceDep,
    settings: SettingsDep,
    depth: int = Query(default=1, ge=1, le=5),
) -> SuccessResponse[list[GraphNodeResponse]]:
    neighbors = await graph.get_neighbors(
        entity_id, workspace_id=workspace_id, depth=depth
    )
    responses = [GraphNodeResponse.model_validate(n) for n in neighbors]
    return build_success_response(responses, settings=settings)


@router.get(
    "/{entity_id}/similar",
    response_model=SuccessResponse[list[SearchHitResponse]],
    dependencies=[Depends(require_permission("entities:read"))],
)
async def get_similar_entities(
    entity_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    hybrid: HybridSearchServiceDep,
    settings: SettingsDep,
    limit: int = Query(default=10, ge=1, le=50),
) -> SuccessResponse[list[SearchHitResponse]]:
    """Similar Entities — CIS Phase 3 Prompt 2's requirement: vector
    similarity against ``entity_id``'s own entity-description embedding
    (see
    cerebrum.application.semantic.hybrid_search_service.HybridSearchService.similar_to_source),
    not a fresh text query.
    """
    hits = await hybrid.similar_to_source(
        kind=EmbeddingKind.ENTITY_DESCRIPTION.value,
        source_id=entity_id,
        workspace_id=workspace_id,
        limit=limit,
    )
    responses = [SearchHitResponse.from_hit(hit) for hit in hits]
    return build_success_response(responses, settings=settings)
