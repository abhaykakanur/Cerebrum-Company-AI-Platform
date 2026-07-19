"""The Retrieval Engine API surface — CIS Phase 3 Prompt 3's Retrieval
Engine, Context Builder, Ranking, and Explainability, layered entirely
on top of CIS Phase 3 Prompt 1's Knowledge Graph and CIS Phase 3 Prompt
2's Semantic Intelligence services (see
cerebrum.application.retrieval's package docstring). Query-time only —
no route here mutates anything.

Reuses the ``"search:read"`` permission code
cerebrum.api.v1.semantic's routes already use — retrieval is another
read-only query capability over the same indexed data, not a new
permission domain.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from cerebrum.api.openapi_responses import STANDARD_ERROR_RESPONSES
from cerebrum.api.response_builder import build_success_response
from cerebrum.api.schemas.envelope import SuccessResponse
from cerebrum.api.schemas.retrieval import (
    ContextPackageResponse,
    EnrichedCitationResponse,
    ExplanationResponse,
    RankedResultResponse,
    RetrievalStatisticsResponse,
)
from cerebrum.application.retrieval.retrieval_service import RetrievalStrategy
from cerebrum.dependencies.auth import WorkspaceIdDep, require_permission
from cerebrum.dependencies.knowledge_graph import KnowledgeGraphServiceDep
from cerebrum.dependencies.retrieval import (
    CitationServiceDep,
    ContextBuilderServiceDep,
    ExplainabilityServiceDep,
    RankingServiceDep,
    RetrievalServiceDep,
)
from cerebrum.dependencies.semantic import (
    HybridSearchServiceDep,
    SearchServiceDep,
    VectorIndexServiceDep,
)
from cerebrum.dependencies.settings import SettingsDep
from cerebrum.infrastructure.embeddings.kind import EmbeddingKind

router = APIRouter(
    prefix="/retrieval", tags=["Retrieval"], responses=STANDARD_ERROR_RESPONSES
)

_read = Depends(require_permission("search:read"))


@router.get(
    "/retrieve",
    response_model=SuccessResponse[list[RankedResultResponse]],
    dependencies=[_read],
)
async def retrieve(
    workspace_id: WorkspaceIdDep,
    retrieval: RetrievalServiceDep,
    ranking: RankingServiceDep,
    settings: SettingsDep,
    q: Annotated[str | None, Query()] = None,
    strategy: Annotated[RetrievalStrategy, Query()] = RetrievalStrategy.HYBRID,
    kinds: Annotated[list[str] | None, Query()] = None,
    tags: Annotated[list[str] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    vector_weight: Annotated[float, Query(ge=0.0)] = 1.0,
    keyword_weight: Annotated[float, Query(ge=0.0)] = 1.0,
    entity_id: Annotated[uuid.UUID | None, Query()] = None,
    depth: Annotated[int, Query(ge=1, le=5)] = 1,
) -> SuccessResponse[list[RankedResultResponse]]:
    """Retrieve Context — CIS Phase 3 Prompt 3's core Retrieval Engine
    endpoint: runs the requested strategy, then ranks results by the
    eight-factor weighted score (see
    cerebrum.application.retrieval.ranking_service.RankingService).
    """
    result = await retrieval.retrieve(
        q,
        workspace_id=workspace_id,
        strategy=strategy,
        kinds=kinds,
        tags=tags,
        limit=limit,
        vector_weight=vector_weight,
        keyword_weight=keyword_weight,
        entity_id=entity_id,
        depth=depth,
    )
    neighbor_ids = (
        {hit.source_id for hit in result.hits}
        if strategy is RetrievalStrategy.GRAPH
        else None
    )
    ranked = ranking.rank(result.hits, graph_neighbor_ids=neighbor_ids)
    return build_success_response(
        [RankedResultResponse.from_ranked(r) for r in ranked], settings=settings
    )


@router.get(
    "/context",
    response_model=SuccessResponse[ContextPackageResponse],
    dependencies=[_read],
)
async def build_context_package(
    workspace_id: WorkspaceIdDep,
    retrieval: RetrievalServiceDep,
    context_builder: ContextBuilderServiceDep,
    citation_service: CitationServiceDep,
    settings: SettingsDep,
    q: Annotated[str | None, Query()] = None,
    strategy: Annotated[RetrievalStrategy, Query()] = RetrievalStrategy.HYBRID,
    kinds: Annotated[list[str] | None, Query()] = None,
    tags: Annotated[list[str] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    entity_id: Annotated[uuid.UUID | None, Query()] = None,
    depth: Annotated[int, Query(ge=1, le=5)] = 1,
    max_chunks: Annotated[int, Query(ge=1, le=200)] = 20,
    max_entities: Annotated[int, Query(ge=1, le=200)] = 20,
    max_characters: Annotated[int, Query(ge=100, le=100_000)] = 8000,
    graph_depth: Annotated[int, Query(ge=0, le=5)] = 0,
    include_version_history: Annotated[bool, Query()] = False,
) -> SuccessResponse[ContextPackageResponse]:
    """Build Context Package — CIS Phase 3 Prompt 3's Context Builder:
    runs retrieval, then resolves the full documents/chunks/entities/
    relationships those results reference into one structured,
    size-bounded package — see
    cerebrum.application.retrieval.context_builder_service's docstring
    for the optimization techniques applied.
    """
    result = await retrieval.retrieve(
        q,
        workspace_id=workspace_id,
        strategy=strategy,
        kinds=kinds,
        tags=tags,
        limit=limit,
        entity_id=entity_id,
        depth=depth,
    )
    package = await context_builder.build(
        result.hits,
        workspace_id=workspace_id,
        query_text=q,
        max_chunks=max_chunks,
        max_entities=max_entities,
        max_characters=max_characters,
        graph_depth=graph_depth,
        include_version_history=include_version_history,
    )
    enriched_citations = await citation_service.build_citations(
        result.hits, workspace_id=workspace_id
    )
    return build_success_response(
        ContextPackageResponse.from_package(
            package,
            citations=[
                EnrichedCitationResponse.from_citation(c) for c in enriched_citations
            ],
        ),
        settings=settings,
    )


@router.get(
    "/explain",
    response_model=SuccessResponse[list[ExplanationResponse]],
    dependencies=[_read],
)
async def explain_retrieval(
    workspace_id: WorkspaceIdDep,
    retrieval: RetrievalServiceDep,
    ranking: RankingServiceDep,
    explainability: ExplainabilityServiceDep,
    settings: SettingsDep,
    q: Annotated[str | None, Query()] = None,
    strategy: Annotated[RetrievalStrategy, Query()] = RetrievalStrategy.HYBRID,
    kinds: Annotated[list[str] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    entity_id: Annotated[uuid.UUID | None, Query()] = None,
    depth: Annotated[int, Query(ge=1, le=5)] = 1,
) -> SuccessResponse[list[ExplanationResponse]]:
    """Explain Retrieval — CIS Phase 3 Prompt 3's Explainability: why
    each result was selected, its full ranking-factor breakdown, the
    strategy used, supporting evidence, and a confidence breakdown —
    see cerebrum.application.retrieval.explainability_service.
    """
    result = await retrieval.retrieve(
        q,
        workspace_id=workspace_id,
        strategy=strategy,
        kinds=kinds,
        limit=limit,
        entity_id=entity_id,
        depth=depth,
    )
    ranked = ranking.rank(result.hits)
    explanations = explainability.explain_batch(ranked, strategy=strategy.value)
    return build_success_response(
        [ExplanationResponse.from_explanation(e) for e in explanations],
        settings=settings,
    )


@router.get(
    "/similar-entities/{entity_id}",
    response_model=SuccessResponse[list[RankedResultResponse]],
    dependencies=[_read],
)
async def similar_entities(
    entity_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    retrieval: RetrievalServiceDep,
    ranking: RankingServiceDep,
    settings: SettingsDep,
    depth: Annotated[int, Query(ge=1, le=5)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> SuccessResponse[list[RankedResultResponse]]:
    """Similar Entities — graph-assisted retrieval: entities within
    ``depth`` hops of ``entity_id`` in the knowledge graph (see
    cerebrum.application.retrieval.retrieval_service.RetrievalService's
    ``GRAPH`` strategy), ranked with graph proximity as a first-class
    factor rather than
    cerebrum.api.v1.entities's pure-vector ``/similar`` endpoint.
    """
    result = await retrieval.retrieve(
        workspace_id=workspace_id,
        strategy=RetrievalStrategy.GRAPH,
        entity_id=entity_id,
        depth=depth,
        limit=limit,
    )
    neighbor_ids = {hit.source_id for hit in result.hits}
    ranked = ranking.rank(result.hits, graph_neighbor_ids=neighbor_ids)
    return build_success_response(
        [RankedResultResponse.from_ranked(r) for r in ranked], settings=settings
    )


@router.get(
    "/similar-documents/{document_version_id}",
    response_model=SuccessResponse[list[RankedResultResponse]],
    dependencies=[_read],
)
async def similar_documents(
    document_version_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    hybrid: HybridSearchServiceDep,
    ranking: RankingServiceDep,
    settings: SettingsDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> SuccessResponse[list[RankedResultResponse]]:
    """Similar Documents — semantic similarity against
    ``document_version_id``'s document-summary embedding (see
    cerebrum.api.v1.documents's identical Prompt 2 endpoint), ranked
    through the same multi-factor scoring every other Retrieval Engine
    endpoint uses, for a consistent ``final_score``/explanation shape.
    """
    hits = await hybrid.similar_to_source(
        kind=EmbeddingKind.DOCUMENT_SUMMARY.value,
        source_id=document_version_id,
        workspace_id=workspace_id,
        limit=limit,
    )
    ranked = ranking.rank(hits)
    return build_success_response(
        [RankedResultResponse.from_ranked(r) for r in ranked], settings=settings
    )


@router.get(
    "/graph-context/{entity_id}",
    response_model=SuccessResponse[ContextPackageResponse],
    dependencies=[_read],
)
async def graph_context(
    entity_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    retrieval: RetrievalServiceDep,
    context_builder: ContextBuilderServiceDep,
    citation_service: CitationServiceDep,
    settings: SettingsDep,
    depth: Annotated[int, Query(ge=1, le=5)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> SuccessResponse[ContextPackageResponse]:
    """Graph Context — a :class:`~cerebrum.api.schemas.retrieval.ContextPackageResponse`
    built entirely from graph-assisted retrieval outward from one seed
    entity: its neighbors (as entities), the relationships among them,
    and a further graph-neighbor expansion at ``depth``.
    """
    result = await retrieval.retrieve(
        workspace_id=workspace_id,
        strategy=RetrievalStrategy.GRAPH,
        entity_id=entity_id,
        depth=depth,
        limit=limit,
    )
    package = await context_builder.build(
        result.hits, workspace_id=workspace_id, graph_depth=depth
    )
    enriched_citations = await citation_service.build_citations(
        result.hits, workspace_id=workspace_id
    )
    return build_success_response(
        ContextPackageResponse.from_package(
            package,
            citations=[
                EnrichedCitationResponse.from_citation(c) for c in enriched_citations
            ],
        ),
        settings=settings,
    )


@router.get(
    "/statistics",
    response_model=SuccessResponse[RetrievalStatisticsResponse],
    dependencies=[_read],
)
async def get_retrieval_statistics(
    workspace_id: WorkspaceIdDep,
    vectors: VectorIndexServiceDep,
    search: SearchServiceDep,
    graph: KnowledgeGraphServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[RetrievalStatisticsResponse]:
    """Retrieval Statistics — combines the vector, search-index, and
    knowledge-graph statistics each underlying service already exposes
    (:class:`~cerebrum.application.semantic.vector_index_service.VectorIndexService`,
    :class:`~cerebrum.application.semantic.search_service.SearchService`,
    :class:`KnowledgeGraphService`) into one response, since every
    retrieval strategy draws on all three.
    """
    vector_stats = await vectors.get_statistics(workspace_id=workspace_id)
    search_stats = await search.get_statistics(workspace_id=workspace_id)
    graph_stats = await graph.get_statistics(workspace_id=workspace_id)
    return build_success_response(
        RetrievalStatisticsResponse(
            vector_count=vector_stats["vector_count"],
            indexed_document_count=search_stats["indexed_document_count"],
            entity_count=graph_stats["entity_count"],
            relationship_count=graph_stats["relationship_count"],
        ),
        settings=settings,
    )
