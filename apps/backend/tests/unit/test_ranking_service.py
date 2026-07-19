"""Proves CIS Phase 3 Prompt 3's ``RankingService``: the eight-factor
weighted score, min-max normalization (including the constant-batch ->
neutral ``0.5`` edge case), the optional graph-proximity/entity-
importance/recency signals degrading gracefully when omitted, and
``entity_degree_from_relationships``'s importance-proxy helper.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from cerebrum.application.retrieval.ranking_service import (
    RankingService,
    entity_degree_from_relationships,
)
from cerebrum.application.semantic.hybrid_search_service import Citation, SearchHit

pytestmark = pytest.mark.unit


def _hit(
    source_id: str,
    *,
    fused_score: float = 0.0,
    vector_score: float | None = None,
    keyword_score: float | None = None,
    confidence: float = 0.5,
    snippet: str = "",
    entity_id: uuid.UUID | None = None,
) -> SearchHit:
    return SearchHit(
        source_id=source_id,
        kind="chunk",
        title="Title",
        snippet=snippet,
        fused_score=fused_score,
        vector_score=vector_score,
        keyword_score=keyword_score,
        citation=Citation(
            document_id=None,
            document_version_id=None,
            chunk_id=None,
            entity_id=entity_id,
            confidence=confidence,
            provenance={},
        ),
    )


def test_rank_empty_returns_empty() -> None:
    assert RankingService().rank([]) == []


def test_rank_orders_by_final_score_descending() -> None:
    hits = [
        _hit("low", fused_score=0.1, vector_score=0.1, keyword_score=1.0),
        _hit("high", fused_score=0.9, vector_score=0.9, keyword_score=9.0),
    ]

    ranked = RankingService().rank(hits)

    assert [r.hit.source_id for r in ranked] == ["high", "low"]
    assert ranked[0].final_score >= ranked[1].final_score


def test_constant_batch_normalizes_to_neutral_factor() -> None:
    hits = [_hit("a", fused_score=0.5), _hit("b", fused_score=0.5)]

    ranked = RankingService().rank(hits)

    assert all(r.factors.hybrid_score == 0.5 for r in ranked)


def test_graph_proximity_factor_set_for_neighbor_entities() -> None:
    neighbor_entity_id = uuid.uuid4()
    other_entity_id = uuid.uuid4()
    hits = [
        _hit("neighbor", entity_id=neighbor_entity_id),
        _hit("other", entity_id=other_entity_id),
    ]

    ranked = RankingService().rank(hits, graph_neighbor_ids={str(neighbor_entity_id)})
    by_id = {r.hit.source_id: r for r in ranked}

    assert by_id["neighbor"].factors.graph_proximity == 1.0
    assert by_id["other"].factors.graph_proximity == 0.0


def test_graph_proximity_defaults_to_zero_without_neighbor_ids() -> None:
    ranked = RankingService().rank([_hit("a", entity_id=uuid.uuid4())])
    assert ranked[0].factors.graph_proximity == 0.0


def test_entity_importance_uses_entity_degree() -> None:
    hits = [_hit("popular"), _hit("obscure")]

    ranked = RankingService().rank(hits, entity_degree={"popular": 10, "obscure": 0})
    by_id = {r.hit.source_id: r for r in ranked}

    assert by_id["popular"].factors.entity_importance == 1.0
    assert by_id["obscure"].factors.entity_importance == 0.0


def test_recency_defaults_to_neutral_when_unknown() -> None:
    ranked = RankingService().rank([_hit("a")])
    assert ranked[0].factors.recency == 0.5


def test_recency_decays_for_older_content() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    hits = [_hit("new"), _hit("old")]
    created_at_by_source = {
        "new": now,
        "old": now - timedelta(days=90),
    }

    ranked = RankingService().rank(
        hits, created_at_by_source=created_at_by_source, now=now
    )
    by_id = {r.hit.source_id: r for r in ranked}

    assert by_id["new"].factors.recency == pytest.approx(1.0)
    assert by_id["old"].factors.recency < by_id["new"].factors.recency


def test_source_confidence_matches_citation_confidence() -> None:
    hits = [_hit("a", confidence=0.42), _hit("b", confidence=0.9)]

    ranked = RankingService().rank(hits)
    by_id = {r.hit.source_id: r for r in ranked}

    assert by_id["a"].factors.source_confidence == 0.42
    assert by_id["b"].factors.source_confidence == 0.9


def test_document_quality_uses_snippet_length_as_proxy() -> None:
    hits = [_hit("short", snippet="hi"), _hit("long", snippet="x" * 500)]

    ranked = RankingService().rank(hits)
    by_id = {r.hit.source_id: r for r in ranked}

    assert by_id["long"].factors.document_quality == 1.0
    assert by_id["short"].factors.document_quality == 0.0


def test_custom_weights_are_respected() -> None:
    hits = [
        _hit("vector_heavy", vector_score=1.0, keyword_score=0.0),
        _hit("keyword_heavy", vector_score=0.0, keyword_score=1.0),
    ]

    ranked = RankingService(weights={"vector_similarity": 1.0}).rank(hits)

    assert ranked[0].hit.source_id == "vector_heavy"


def test_entity_degree_from_relationships_counts_both_sides() -> None:
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    degree = entity_degree_from_relationships([(a, b), (a, c)])

    assert degree[str(a)] == 2
    assert degree[str(b)] == 1
    assert degree[str(c)] == 1
