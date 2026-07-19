"""Proves CIS Phase 3 Prompt 3's ``ExplainabilityService``: the
templated (no-LLM) "why selected" sentence names the actual dominant
ranking factor, the full factor/confidence breakdown round-trips
unchanged, supporting evidence comes from the hit's own snippet, and
``explain_batch`` preserves per-result strategy/order.
"""

import pytest

from cerebrum.application.retrieval.explainability_service import (
    ExplainabilityService,
)
from cerebrum.application.retrieval.ranking_service import RankedResult, RankingFactors
from cerebrum.application.semantic.hybrid_search_service import Citation, SearchHit

pytestmark = pytest.mark.unit


def _ranked(
    *,
    source_id: str = "s1",
    snippet: str = "",
    final_score: float = 0.5,
    **factor_overrides: float,
) -> RankedResult:
    base_factors = {
        "hybrid_score": 0.1,
        "vector_similarity": 0.1,
        "bm25_score": 0.1,
        "graph_proximity": 0.1,
        "entity_importance": 0.1,
        "recency": 0.1,
        "source_confidence": 0.1,
        "document_quality": 0.1,
    }
    base_factors.update(factor_overrides)
    hit = SearchHit(
        source_id=source_id,
        kind="chunk",
        title="Title",
        snippet=snippet,
        fused_score=0.5,
        vector_score=0.5,
        keyword_score=None,
        citation=Citation(
            document_id=None,
            document_version_id=None,
            chunk_id=None,
            entity_id=None,
            confidence=0.5,
            provenance={},
        ),
    )
    return RankedResult(
        hit=hit, factors=RankingFactors(**base_factors), final_score=final_score
    )


def test_why_selected_names_the_dominant_factor() -> None:
    ranked = _ranked(vector_similarity=0.95)

    explanation = ExplainabilityService().explain(ranked, strategy="semantic")

    assert "semantic similarity" in explanation.why_selected
    assert "0.95" in explanation.why_selected


def test_why_selected_switches_with_a_different_dominant_factor() -> None:
    ranked = _ranked(graph_proximity=0.99)

    explanation = ExplainabilityService().explain(ranked, strategy="graph")

    assert "knowledge graph" in explanation.why_selected


def test_confidence_breakdown_matches_factors() -> None:
    ranked = _ranked(bm25_score=0.6)

    explanation = ExplainabilityService().explain(ranked, strategy="keyword")

    assert explanation.confidence_breakdown == ranked.factors.as_dict()
    assert explanation.ranking_factors == ranked.factors
    assert explanation.final_score == ranked.final_score
    assert explanation.strategy == "keyword"


def test_supporting_evidence_uses_snippet_when_present() -> None:
    ranked = _ranked(snippet="Acme signed the deal.")

    explanation = ExplainabilityService().explain(ranked, strategy="hybrid")

    assert explanation.supporting_evidence == ["Acme signed the deal."]


def test_supporting_evidence_empty_without_a_snippet() -> None:
    ranked = _ranked(snippet="")

    explanation = ExplainabilityService().explain(ranked, strategy="hybrid")

    assert explanation.supporting_evidence == []


def test_explain_batch_preserves_order_and_strategy() -> None:
    ranked_results = [_ranked(source_id="a"), _ranked(source_id="b")]

    explanations = ExplainabilityService().explain_batch(
        ranked_results, strategy="metadata"
    )

    assert [e.source_id for e in explanations] == ["a", "b"]
    assert all(e.strategy == "metadata" for e in explanations)
