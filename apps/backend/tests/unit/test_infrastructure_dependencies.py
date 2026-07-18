"""Proves CIS Phase 1 Prompt 7's Testing improvement: the infrastructure
client dependency providers (cerebrum.dependencies.infrastructure) were
real, working one-line adapters with zero direct test coverage — no
route consumes a raw Redis/Neo4j/Qdrant/MinIO/OpenSearch client yet (no
business feature exists), but each provider is exactly the kind of
thin-but-load-bearing wiring a typo could silently break.
"""

from types import SimpleNamespace

import pytest

from cerebrum.dependencies.infrastructure import (
    get_metrics_registry,
    get_minio,
    get_neo4j,
    get_opensearch,
    get_qdrant,
    get_redis,
    get_tracer,
)

pytestmark = pytest.mark.unit


def _fake_state() -> SimpleNamespace:
    return SimpleNamespace(
        redis=SimpleNamespace(client="redis-client"),
        neo4j=SimpleNamespace(client="neo4j-client"),
        qdrant=SimpleNamespace(client="qdrant-client"),
        minio=SimpleNamespace(client="minio-client"),
        opensearch=SimpleNamespace(client="opensearch-client"),
        metrics="metrics-registry",
        tracer="tracer",
    )


def test_get_redis_returns_the_state_managers_client() -> None:
    assert get_redis(_fake_state()) == "redis-client"  # type: ignore[arg-type]


def test_get_neo4j_returns_the_state_managers_client() -> None:
    assert get_neo4j(_fake_state()) == "neo4j-client"  # type: ignore[arg-type]


def test_get_qdrant_returns_the_state_managers_client() -> None:
    assert get_qdrant(_fake_state()) == "qdrant-client"  # type: ignore[arg-type]


def test_get_minio_returns_the_state_managers_client() -> None:
    assert get_minio(_fake_state()) == "minio-client"  # type: ignore[arg-type]


def test_get_opensearch_returns_the_state_managers_client() -> None:
    assert get_opensearch(_fake_state()) == "opensearch-client"  # type: ignore[arg-type]


def test_get_metrics_registry_returns_the_state_metrics() -> None:
    assert get_metrics_registry(_fake_state()) == "metrics-registry"  # type: ignore[arg-type]


def test_get_tracer_returns_the_state_tracer() -> None:
    assert get_tracer(_fake_state()) == "tracer"  # type: ignore[arg-type]
