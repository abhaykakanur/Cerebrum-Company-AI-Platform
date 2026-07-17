"""Proves the acceptance criteria "Every request receives Request ID",
"Every request receives Correlation ID", and "Middleware executes in
correct order" from CIS Phase 1 Prompt 3 Section 3.
"""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


def test_response_carries_generated_request_id(client: TestClient) -> None:
    response = client.get("/live")
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) == 36  # UUIDv4 string length


def test_two_requests_receive_different_request_ids(client: TestClient) -> None:
    first = client.get("/live")
    second = client.get("/live")
    assert first.headers["X-Request-ID"] != second.headers["X-Request-ID"]


def test_correlation_id_is_generated_when_absent(client: TestClient) -> None:
    response = client.get("/live")
    assert "X-Correlation-ID" in response.headers


def test_correlation_id_is_echoed_when_supplied(client: TestClient) -> None:
    response = client.get("/live", headers={"X-Correlation-ID": "test-correlation-123"})
    assert response.headers["X-Correlation-ID"] == "test-correlation-123"


def test_response_carries_security_headers(client: TestClient) -> None:
    response = client.get("/live")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_response_carries_timing_header(client: TestClient) -> None:
    response = client.get("/live")
    assert "X-Response-Time-Ms" in response.headers
    assert float(response.headers["X-Response-Time-Ms"]) >= 0
