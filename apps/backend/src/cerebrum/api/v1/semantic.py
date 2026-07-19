"""Workspace-level Semantic Intelligence queries — CIS Phase 3 Prompt
2's Semantic Search, Hybrid Search, Autocomplete, and Search Statistics
APIs. Per-artifact "similar to this" queries live on
cerebrum.api.v1.documents (similar documents/chunks) and
cerebrum.api.v1.entities (similar entities) instead, next to the rest
of each artifact's endpoints — see cerebrum.api.v1.entities's docstring
for the same "per-artifact queries live with the artifact" convention.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from cerebrum.api.openapi_responses import STANDARD_ERROR_RESPONSES
from cerebrum.api.response_builder import build_success_response
from cerebrum.api.schemas.envelope import SuccessResponse
from cerebrum.api.schemas.semantic import (
    AutocompleteResponse,
    SearchHitResponse,
    SemanticStatisticsResponse,
)
from cerebrum.dependencies.auth import WorkspaceIdDep, require_permission
from cerebrum.dependencies.semantic import (
    HybridSearchServiceDep,
    SearchServiceDep,
    VectorIndexServiceDep,
)
from cerebrum.dependencies.settings import SettingsDep

router = APIRouter(
    prefix="/search", tags=["Semantic Search"], responses=STANDARD_ERROR_RESPONSES
)


@router.get(
    "/semantic",
    response_model=SuccessResponse[list[SearchHitResponse]],
    dependencies=[Depends(require_permission("search:read"))],
)
async def semantic_search(
    workspace_id: WorkspaceIdDep,
    hybrid: HybridSearchServiceDep,
    settings: SettingsDep,
    q: Annotated[str, Query(min_length=1)],
    kinds: Annotated[list[str] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> SuccessResponse[list[SearchHitResponse]]:
    """Pure vector (cosine-similarity) search — CIS Phase 3 Prompt 2's
    Semantic Search endpoint. Implemented as
    :meth:`~cerebrum.application.semantic.hybrid_search_service.HybridSearchService.search`
    with ``keyword_weight=0``, so results are ranked by semantic
    similarity alone.
    """
    hits = await hybrid.search(
        q, workspace_id=workspace_id, kinds=kinds, limit=limit, keyword_weight=0.0
    )
    return build_success_response(
        [SearchHitResponse.from_hit(h) for h in hits], settings=settings
    )


@router.get(
    "/hybrid",
    response_model=SuccessResponse[list[SearchHitResponse]],
    dependencies=[Depends(require_permission("search:read"))],
)
async def hybrid_search(
    workspace_id: WorkspaceIdDep,
    hybrid: HybridSearchServiceDep,
    settings: SettingsDep,
    q: Annotated[str, Query(min_length=1)],
    kinds: Annotated[list[str] | None, Query()] = None,
    tags: Annotated[list[str] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    vector_weight: Annotated[float, Query(ge=0.0)] = 1.0,
    keyword_weight: Annotated[float, Query(ge=0.0)] = 1.0,
) -> SuccessResponse[list[SearchHitResponse]]:
    """Hybrid Search — CIS Phase 3 Prompt 2's requirement: vector and
    keyword results combined via configurable-weight Reciprocal Rank
    Fusion (see
    cerebrum.application.semantic.hybrid_search_service's docstring).
    """
    hits = await hybrid.search(
        q,
        workspace_id=workspace_id,
        kinds=kinds,
        tags=tags,
        limit=limit,
        vector_weight=vector_weight,
        keyword_weight=keyword_weight,
    )
    return build_success_response(
        [SearchHitResponse.from_hit(h) for h in hits], settings=settings
    )


@router.get(
    "/autocomplete",
    response_model=SuccessResponse[AutocompleteResponse],
    dependencies=[Depends(require_permission("search:read"))],
)
async def autocomplete(
    workspace_id: WorkspaceIdDep,
    search: SearchServiceDep,
    settings: SettingsDep,
    prefix: Annotated[str, Query(min_length=1)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> SuccessResponse[AutocompleteResponse]:
    suggestions = await search.autocomplete(
        prefix=prefix, workspace_id=workspace_id, limit=limit
    )
    return build_success_response(
        AutocompleteResponse(suggestions=suggestions), settings=settings
    )


@router.get(
    "/statistics",
    response_model=SuccessResponse[SemanticStatisticsResponse],
    dependencies=[Depends(require_permission("search:read"))],
)
async def get_semantic_statistics(
    workspace_id: WorkspaceIdDep,
    vectors: VectorIndexServiceDep,
    search: SearchServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[SemanticStatisticsResponse]:
    vector_stats = await vectors.get_statistics(workspace_id=workspace_id)
    search_stats = await search.get_statistics(workspace_id=workspace_id)
    return build_success_response(
        SemanticStatisticsResponse(
            vector_count=vector_stats["vector_count"],
            indexed_document_count=search_stats["indexed_document_count"],
        ),
        settings=settings,
    )
