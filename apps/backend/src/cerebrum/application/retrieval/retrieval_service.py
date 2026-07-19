"""``RetrievalService``: CIS Phase 3 Prompt 3's Retrieval Engine — one
entry point (:meth:`RetrievalService.retrieve`) over five retrieval
strategies, each backed by an already-built CIS Phase 3 Prompt 1/2
service rather than new query infrastructure:

- ``HYBRID``/``SEMANTIC``/``KEYWORD`` delegate to
  :class:`~cerebrum.application.semantic.hybrid_search_service.HybridSearchService.search`
  with the vector/keyword weights that make it behave as each named
  strategy (semantic = vector-only, keyword = keyword-only, hybrid =
  both, RRF-fused).
- ``GRAPH`` (graph-assisted retrieval) walks
  :class:`~cerebrum.application.knowledge_graph.knowledge_graph_service.KnowledgeGraphService`'s
  Neo4j-backed neighbor graph outward from a seed entity, turning each
  neighbor into a
  :class:`~cerebrum.application.semantic.hybrid_search_service.SearchHit`
  directly from the graph node's own properties — no second Postgres/
  vector round-trip needed for the neighbor list itself.
- ``METADATA`` delegates to
  :class:`~cerebrum.application.semantic.search_service.SearchService.search_by_metadata`
  — a filter-only (kind/tag/date-range), no-text-query OpenSearch
  query, for "show me everything tagged X" retrieval that has no query
  text to rank against.

Every strategy returns the same :class:`RetrievalResult` shape (a list
of ``SearchHit``, each already carrying its Citation — see
``HybridSearchService``'s docstring), so
:class:`~cerebrum.application.retrieval.ranking_service.RankingService`,
:class:`~cerebrum.application.retrieval.context_builder_service.ContextBuilderService`,
and
:class:`~cerebrum.application.retrieval.explainability_service.ExplainabilityService`
never need to know which strategy produced the hits they're processing.
"""

import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from cerebrum.application.knowledge_graph.knowledge_graph_service import (
    KnowledgeGraphService,
)
from cerebrum.application.retrieval.events import RetrievalCompletedEvent
from cerebrum.application.semantic.hybrid_search_service import (
    Citation,
    HybridSearchService,
    SearchHit,
)
from cerebrum.application.semantic.search_service import SearchService
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.shared.errors.exceptions import ValidationException


class RetrievalStrategy(StrEnum):
    HYBRID = "hybrid"
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    GRAPH = "graph"
    METADATA = "metadata"


_TEXT_STRATEGIES = frozenset(
    (RetrievalStrategy.HYBRID, RetrievalStrategy.SEMANTIC, RetrievalStrategy.KEYWORD)
)


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    hits: list[SearchHit]
    strategy: RetrievalStrategy
    query_text: str | None
    seed_entity_id: uuid.UUID | None = None


class RetrievalService:
    def __init__(
        self,
        *,
        hybrid_search_service: HybridSearchService,
        knowledge_graph_service: KnowledgeGraphService,
        search_service: SearchService,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._hybrid = hybrid_search_service
        self._graph = knowledge_graph_service
        self._search = search_service
        self._events = event_dispatcher

    async def retrieve(
        self,
        query_text: str | None = None,
        *,
        workspace_id: uuid.UUID,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        kinds: list[str] | None = None,
        tags: list[str] | None = None,
        limit: int = 10,
        vector_weight: float = 1.0,
        keyword_weight: float = 1.0,
        entity_id: uuid.UUID | None = None,
        depth: int = 1,
    ) -> RetrievalResult:
        if strategy in _TEXT_STRATEGIES:
            if not query_text:
                raise ValidationException(
                    f"{strategy.value} retrieval requires query_text."
                )
            hits = await self._text_retrieve(
                query_text,
                strategy=strategy,
                workspace_id=workspace_id,
                kinds=kinds,
                tags=tags,
                limit=limit,
                vector_weight=vector_weight,
                keyword_weight=keyword_weight,
            )
        elif strategy is RetrievalStrategy.GRAPH:
            if entity_id is None:
                raise ValidationException("Graph retrieval requires entity_id.")
            hits = await self._graph_retrieve(
                entity_id, workspace_id=workspace_id, depth=depth, limit=limit
            )
        else:
            hits = await self._metadata_retrieve(
                workspace_id=workspace_id, kinds=kinds, tags=tags, limit=limit
            )

        self._events.publish(
            RetrievalCompletedEvent(
                workspace_id=workspace_id,
                strategy=strategy.value,
                query_text=query_text,
                result_count=len(hits),
            )
        )
        return RetrievalResult(
            hits=hits,
            strategy=strategy,
            query_text=query_text,
            seed_entity_id=entity_id,
        )

    async def _text_retrieve(
        self,
        query_text: str,
        *,
        strategy: RetrievalStrategy,
        workspace_id: uuid.UUID,
        kinds: list[str] | None,
        tags: list[str] | None,
        limit: int,
        vector_weight: float,
        keyword_weight: float,
    ) -> list[SearchHit]:
        weights = {
            RetrievalStrategy.HYBRID: (vector_weight, keyword_weight),
            RetrievalStrategy.SEMANTIC: (vector_weight, 0.0),
            RetrievalStrategy.KEYWORD: (0.0, keyword_weight),
        }[strategy]
        vw, kw = weights
        return await self._hybrid.search(
            query_text,
            workspace_id=workspace_id,
            kinds=kinds,
            tags=tags,
            limit=limit,
            vector_weight=vw,
            keyword_weight=kw,
        )

    async def _graph_retrieve(
        self,
        entity_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        depth: int,
        limit: int,
    ) -> list[SearchHit]:
        neighbors = await self._graph.get_neighbors(
            entity_id, workspace_id=workspace_id, depth=depth
        )
        return [self._hit_from_neighbor(node) for node in neighbors[:limit]]

    async def _metadata_retrieve(
        self,
        *,
        workspace_id: uuid.UUID,
        kinds: list[str] | None,
        tags: list[str] | None,
        limit: int,
    ) -> list[SearchHit]:
        response = await self._search.search_by_metadata(
            workspace_id=workspace_id, kinds=kinds, tags=tags, limit=limit
        )
        hits = []
        for hit in response.get("hits", {}).get("hits", []):
            source = hit["_source"]
            hits.append(
                SearchHit(
                    source_id=source["source_id"],
                    kind=source["kind"],
                    title=source.get("title", ""),
                    snippet=source.get("content", "")[:200],
                    fused_score=0.0,
                    vector_score=None,
                    keyword_score=None,
                    citation=Citation(
                        document_id=_maybe_uuid(source.get("document_id")),
                        document_version_id=_maybe_uuid(
                            source.get("document_version_id")
                        ),
                        chunk_id=_maybe_uuid(source.get("chunk_id")),
                        entity_id=_maybe_uuid(source.get("entity_id")),
                        confidence=1.0,
                        provenance={"index": "opensearch", "strategy": "metadata"},
                    ),
                )
            )
        return hits

    @staticmethod
    def _hit_from_neighbor(node: dict[str, Any]) -> SearchHit:
        entity_id = uuid.UUID(str(node["id"]))
        confidence = float(node.get("confidence", 0.0))
        return SearchHit(
            source_id=str(entity_id),
            kind="entity",
            title=str(node.get("canonical_name", "")),
            snippet="",
            fused_score=0.0,
            vector_score=None,
            keyword_score=None,
            citation=Citation(
                document_id=None,
                document_version_id=None,
                chunk_id=None,
                entity_id=entity_id,
                confidence=confidence,
                provenance={"index": "neo4j", "strategy": "graph"},
            ),
        )


def _maybe_uuid(value: str | None) -> uuid.UUID | None:
    return uuid.UUID(value) if value else None
