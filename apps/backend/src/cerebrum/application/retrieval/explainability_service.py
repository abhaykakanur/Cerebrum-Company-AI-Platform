"""``ExplainabilityService``: CIS Phase 3 Prompt 3's Explainability —
for each
:class:`~cerebrum.application.retrieval.ranking_service.RankedResult`,
produces an :class:`Explanation` naming which retrieval strategy found
it, a plain-language "why selected" sentence naming its single
strongest ranking factor, the full ranking-factor breakdown, its
supporting evidence (the hit's snippet — the only text this service
has without a second content round-trip), and a confidence breakdown.

The "why selected" sentence is template-generated from
:class:`~cerebrum.application.retrieval.ranking_service.RankingFactors`'
own values — never an LLM call (see this milestone's Non-Objectives) —
the same deterministic, no-ML approach
cerebrum.application.retrieval.ranking_service.RankingService's
weighted-sum scoring already takes.
"""

from dataclasses import dataclass

from cerebrum.application.retrieval.ranking_service import RankedResult, RankingFactors

_FACTOR_LABELS: dict[str, str] = {
    "hybrid_score": "its combined vector+keyword rank",
    "vector_similarity": "strong semantic similarity to the query",
    "bm25_score": "strong keyword/full-text match",
    "graph_proximity": "proximity to the seed entity in the knowledge graph",
    "entity_importance": "being a highly-connected entity",
    "recency": "being recently created",
    "source_confidence": "high extraction/indexing confidence",
    "document_quality": "substantial source content",
}


@dataclass(frozen=True, slots=True)
class Explanation:
    source_id: str
    strategy: str
    why_selected: str
    ranking_factors: RankingFactors
    supporting_evidence: list[str]
    confidence_breakdown: dict[str, float]
    final_score: float


class ExplainabilityService:
    def explain(self, ranked: RankedResult, *, strategy: str) -> Explanation:
        factors = ranked.factors.as_dict()
        dominant_name = max(factors, key=lambda name: factors[name])
        dominant_value = factors[dominant_name]
        why_selected = (
            f"Retrieved via {strategy} strategy; the strongest signal was "
            f"{_FACTOR_LABELS.get(dominant_name, dominant_name)} "
            f"(score {dominant_value:.2f})."
        )
        return Explanation(
            source_id=ranked.hit.source_id,
            strategy=strategy,
            why_selected=why_selected,
            ranking_factors=ranked.factors,
            supporting_evidence=[ranked.hit.snippet] if ranked.hit.snippet else [],
            confidence_breakdown=factors,
            final_score=ranked.final_score,
        )

    def explain_batch(
        self, ranked_results: list[RankedResult], *, strategy: str
    ) -> list[Explanation]:
        return [self.explain(result, strategy=strategy) for result in ranked_results]
