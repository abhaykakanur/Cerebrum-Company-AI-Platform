"""Proves the acceptance criteria "Backend starts successfully",
"Health endpoints respond", and "All infrastructure clients initialize"
from CIS Phase 1 Prompt 3 and CIS Phase 1 Prompt 4.

No real datastore is reachable in this unit-test environment (see
apps/backend/tests/conftest.py's low retry/timeout overrides) — every
client manager is expected to fail its connection attempt gracefully and
report ``unavailable``, never crash application startup. Tests that need
a *healthy* component monkeypatch that one manager's ``health_check``
directly, proving the reporting path works without requiring live
infrastructure.
"""

import pytest
from fastapi.testclient import TestClient

from cerebrum.infrastructure.health import ComponentHealth

pytestmark = pytest.mark.unit

_DATASTORE_NAMES = {"postgresql", "neo4j", "redis", "qdrant", "minio", "opensearch"}


def test_liveness_reports_alive(client: TestClient) -> None:
    response = client.get("/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_readiness_reports_not_ready_when_postgres_unreachable(
    client: TestClient,
) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "not_ready"


def test_readiness_reports_ready_when_postgres_healthy(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _fake_healthy() -> ComponentHealth:
        return ComponentHealth(name="postgresql", status="healthy", latency_ms=1.0)

    monkeypatch.setattr(
        client.app.state.cerebrum.database, "health_check", _fake_healthy
    )
    response = client.get("/ready")
    assert response.json()["status"] == "ready"


def test_health_reports_every_datastore_as_unavailable(client: TestClient) -> None:
    """No infrastructure is reachable in this test environment — every
    client manager's connect() attempt fails, so every component reports
    "unavailable" and the overall status is "unhealthy". See this
    module's docstring.
    """
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unhealthy"
    component_names = {component["name"] for component in body["components"]}
    assert component_names == _DATASTORE_NAMES
    assert all(component["status"] == "unavailable" for component in body["components"])


def test_health_reports_degraded_when_some_components_are_healthy(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _fake_healthy() -> ComponentHealth:
        return ComponentHealth(name="postgresql", status="healthy", latency_ms=1.0)

    monkeypatch.setattr(
        client.app.state.cerebrum.database, "health_check", _fake_healthy
    )
    response = client.get("/health")
    body = response.json()
    assert body["status"] == "degraded"
    postgres_entry = next(c for c in body["components"] if c["name"] == "postgresql")
    assert postgres_entry["status"] == "healthy"


def test_api_v1_root_is_reachable(client: TestClient) -> None:
    response = client.get("/api/v1/")
    assert response.status_code == 200
