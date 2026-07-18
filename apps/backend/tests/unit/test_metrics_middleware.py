"""Proves CIS Phase 1 Prompt 6's API Metrics acceptance criterion and CIS
Phase 1 Prompt 7's Tracing Hooks addition:
cerebrum.middleware.metrics.APIMetricsMiddleware records Request Count,
Latency, Status Codes, Endpoint Usage, and Response Size through the
:class:`~cerebrum.core.observability.MetricsRegistry` port, and opens one
span per request through the
:class:`~cerebrum.core.observability.Tracer` port. Swaps the real
(no-op) :class:`~cerebrum.core.observability.NoOpMetricsRegistry`/
:class:`~cerebrum.core.observability.NoOpTracer` for in-memory recorders
on the already-started application state, the same substitution point a
real Prometheus/OpenTelemetry adapter would occupy.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


class _RecordingMetricsRegistry:
    def __init__(self) -> None:
        self.counters: list[tuple[str, float, dict[str, str] | None]] = []
        self.histograms: list[tuple[str, float, dict[str, str] | None]] = []

    def increment_counter(
        self, name: str, *, value: float = 1.0, labels: dict[str, str] | None = None
    ) -> None:
        self.counters.append((name, value, labels))

    def set_gauge(
        self, name: str, value: float, *, labels: dict[str, str] | None = None
    ) -> None:
        return None

    def observe_histogram(
        self, name: str, value: float, *, labels: dict[str, str] | None = None
    ) -> None:
        self.histograms.append((name, value, labels))


class _RecordingTracer:
    def __init__(self) -> None:
        self.opened_spans: list[str] = []
        self.closed_spans: list[str] = []

    @contextmanager
    def start_span(self, name: str) -> Iterator[None]:
        self.opened_spans.append(name)
        try:
            yield None
        finally:
            self.closed_spans.append(name)


def _install_recorder(app: FastAPI) -> _RecordingMetricsRegistry:
    recorder = _RecordingMetricsRegistry()
    app.state.cerebrum.metrics = recorder
    return recorder


def _install_tracer(app: FastAPI) -> _RecordingTracer:
    tracer = _RecordingTracer()
    app.state.cerebrum.tracer = tracer
    return tracer


def test_request_count_is_recorded(app: FastAPI, client: TestClient) -> None:
    recorder = _install_recorder(app)

    response = client.get("/live")

    assert response.status_code == 200
    assert any(name == "api_requests_total" for name, _, _ in recorder.counters)


def test_latency_is_recorded(app: FastAPI, client: TestClient) -> None:
    recorder = _install_recorder(app)

    client.get("/live")

    durations = [
        v for name, v, _ in recorder.histograms if name == "api_request_duration_ms"
    ]
    assert durations
    assert durations[0] >= 0


def test_response_size_is_recorded(app: FastAPI, client: TestClient) -> None:
    recorder = _install_recorder(app)

    client.get("/live")

    sizes = [
        v for name, v, _ in recorder.histograms if name == "api_response_size_bytes"
    ]
    assert sizes
    assert sizes[0] > 0


def test_labels_carry_method_endpoint_and_status_code(
    app: FastAPI, client: TestClient
) -> None:
    recorder = _install_recorder(app)

    client.get("/live")

    _, _, labels = recorder.counters[0]
    assert labels is not None
    assert labels["method"] == "GET"
    assert labels["endpoint"] == "/live"
    assert labels["status_code"] == "200"


def test_endpoint_usage_distinguishes_routes(app: FastAPI, client: TestClient) -> None:
    recorder = _install_recorder(app)

    client.get("/live")
    client.get("/ready")

    endpoints = {labels["endpoint"] for _, _, labels in recorder.counters if labels}
    assert {"/live", "/ready"}.issubset(endpoints)


def test_error_status_codes_are_recorded(app: FastAPI, client: TestClient) -> None:
    recorder = _install_recorder(app)

    response = client.get("/api/v1/auth/me")  # unauthenticated -> 401

    assert response.status_code == 401
    _, _, labels = recorder.counters[-1]
    assert labels is not None
    assert labels["status_code"] == "401"


def test_a_span_is_opened_and_closed_for_every_request(
    app: FastAPI, client: TestClient
) -> None:
    tracer = _install_tracer(app)

    response = client.get("/live")

    assert response.status_code == 200
    assert tracer.opened_spans == ["GET /live"]
    assert tracer.closed_spans == ["GET /live"]


def test_span_is_closed_even_when_the_route_raises(
    app: FastAPI, client: TestClient
) -> None:
    tracer = _install_tracer(app)

    # /api/v1/auth/me raises AuthenticationException when unauthenticated
    # — the span must still close, not leak, on the error path.
    client.get("/api/v1/auth/me")

    assert tracer.opened_spans == tracer.closed_spans
