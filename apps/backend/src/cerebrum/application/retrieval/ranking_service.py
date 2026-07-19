"""``RankingService``: CIS Phase 3 Prompt 3's multi-factor Ranking —
re-scores a batch of already-retrieved
:class:`~cerebrum.application.semantic.hybrid_search_service.SearchHit`
objects against the eight named factors (hybrid score, vector
similarity, BM25, graph proximity, entity importance, recency, source
confidence, document quality) as a deterministic weighted sum — no ML
re-ranker, no LLM (see this milestone's Non-Objectives), the same
"no ML, no LLM" boundary
cerebrum.application.semantic.hybrid_search_service's RRF fusion
already established for CIS Phase 3 Prompt 2.

Every factor is normalized to ``[0, 1]`` before weighting, via min-max
normalization across the batch being ranked (a factor that's constant
across the whole batch — e.g. every hit came from the same strategy —
normalizes to a neutral ``0.5`` rather than dividing by zero). Factors
this service has no real signal for yet (``document_quality`` — no
document-quality model exists anywhere in this codebase) use an honest,
documented heuristic (snippet length as a substance proxy) rather than
a hidden constant, following the same "honest approximation over a
disguised no-op" precedent
cerebrum.application.knowledge.extraction_service's truncation-based
document summary set.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from cerebrum.application.semantic.hybrid_search_service import SearchHit
from cerebrum.utils.clock import utcnow

_DEFAULT_WEIGHTS: dict[str, float] = {
    "hybrid_score": 0.25,
    "vector_similarity": 0.15,
    "bm25_score": 0.10,
    "graph_proximity": 0.15,
    "entity_importance": 0.10,
    "recency": 0.10,
    "source_confidence": 0.10,
    "document_quality": 0.05,
}

_RECENCY_HALF_LIFE_DAYS = 30.0


@dataclass(frozen=True, slots=True)
class RankingFactors:
    hybrid_score: float
    vector_similarity: float
    bm25_score: float
    graph_proximity: float
    entity_importance: float
    recency: float
    source_confidence: float
    document_quality: float

    def as_dict(self) -> dict[str, float]:
        return {
            "hybrid_score": self.hybrid_score,
            "vector_similarity": self.vector_similarity,
            "bm25_score": self.bm25_score,
            "graph_proximity": self.graph_proximity,
            "entity_importance": self.entity_importance,
            "recency": self.recency,
            "source_confidence": self.source_confidence,
            "document_quality": self.document_quality,
        }


@dataclass(frozen=True, slots=True)
class RankedResult:
    hit: SearchHit
    factors: RankingFactors
    final_score: float


class RankingService:
    def __init__(self, *, weights: dict[str, float] | None = None) -> None:
        self._weights = weights or _DEFAULT_WEIGHTS

    def rank(
        self,
        hits: list[SearchHit],
        *,
        graph_neighbor_ids: set[str] | None = None,
        entity_degree: dict[str, int] | None = None,
        created_at_by_source: dict[str, datetime] | None = None,
        now: datetime | None = None,
    ) -> list[RankedResult]:
        """Ranks ``hits`` (already-fused/retrieved results — see
        cerebrum.application.retrieval.retrieval_service.RetrievalService)
        by a weighted sum of the eight factors. ``graph_neighbor_ids``
        (entity IDs within graph-assisted retrieval's neighbor set),
        ``entity_degree`` (a proxy for entity importance — how many
        relationships each entity participates in), and
        ``created_at_by_source`` (for recency) are optional signals a
        caller may already have on hand (e.g.
        cerebrum.application.retrieval.context_builder_service.ContextBuilderService
        resolving full rows anyway); omitted signals degrade gracefully
        to a neutral factor value rather than erroring.
        """
        if not hits:
            return []
        graph_neighbor_ids = graph_neighbor_ids or set()
        entity_degree = entity_degree or {}
        created_at_by_source = created_at_by_source or {}
        reference_time = now or utcnow()

        hybrid_scores = _normalize([h.fused_score for h in hits])
        vector_scores = _normalize([h.vector_score or 0.0 for h in hits])
        bm25_scores = _normalize([h.keyword_score or 0.0 for h in hits])
        degrees = _normalize([float(entity_degree.get(h.source_id, 0)) for h in hits])
        qualities = _normalize([float(len(h.snippet)) for h in hits])

        ranked = []
        for index, hit in enumerate(hits):
            factors = RankingFactors(
                hybrid_score=hybrid_scores[index],
                vector_similarity=vector_scores[index],
                bm25_score=bm25_scores[index],
                graph_proximity=self._graph_proximity(hit, graph_neighbor_ids),
                entity_importance=degrees[index],
                recency=self._recency(hit, created_at_by_source, reference_time),
                source_confidence=hit.citation.confidence,
                document_quality=qualities[index],
            )
            final_score = sum(
                value * self._weights.get(name, 0.0)
                for name, value in factors.as_dict().items()
            )
            ranked.append(
                RankedResult(hit=hit, factors=factors, final_score=final_score)
            )

        ranked.sort(key=lambda result: result.final_score, reverse=True)
        return ranked

    @staticmethod
    def _graph_proximity(hit: SearchHit, graph_neighbor_ids: set[str]) -> float:
        candidate_ids = {hit.source_id}
        if hit.citation.entity_id is not None:
            candidate_ids.add(str(hit.citation.entity_id))
        return 1.0 if candidate_ids & graph_neighbor_ids else 0.0

    @staticmethod
    def _recency(
        hit: SearchHit,
        created_at_by_source: dict[str, datetime],
        reference_time: datetime,
    ) -> float:
        created_at = created_at_by_source.get(hit.source_id)
        if created_at is None:
            return 0.5
        age_days = max((reference_time - created_at).total_seconds() / 86400.0, 0.0)
        return float(0.5 ** (age_days / _RECENCY_HALF_LIFE_DAYS))


def _normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    low, high = min(values), max(values)
    if high == low:
        return [0.5] * len(values)
    return [(value - low) / (high - low) for value in values]


def entity_degree_from_relationships(
    relationships: list[tuple[uuid.UUID, uuid.UUID]],
) -> dict[str, int]:
    """A simple entity-importance proxy: how many relationships each
    entity participates in (as source or target), across whatever
    relationship set the caller already resolved (see
    ``ContextBuilderService``) — no separate graph-centrality query.
    """
    degree: dict[str, int] = {}
    for source_id, target_id in relationships:
        degree[str(source_id)] = degree.get(str(source_id), 0) + 1
        degree[str(target_id)] = degree.get(str(target_id), 0) + 1
    return degree
