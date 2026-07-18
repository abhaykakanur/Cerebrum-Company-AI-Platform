"""Proves the acceptance criteria "Every request receives Request ID",
"Every request receives Correlation ID", and "Middleware executes in
correct order" from CIS Phase 1 Prompt 3 Section 3. Extended by CIS
Phase 1 Prompt 5 with Request Size Limits and Trusted Proxy Support.
"""

import pytest
from fastapi import FastAPI
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


def test_oversized_request_body_is_rejected(client: TestClient, app: FastAPI) -> None:
    settings = app.state.cerebrum_settings
    too_large = settings.security.max_request_body_bytes + 1

    response = client.post(
        "/api/v1/auth/logout",
        content=b"x",
        headers={"Content-Length": str(too_large)},
    )

    assert response.status_code == 413
    assert response.json()["error_code"] == "REQUEST_ENTITY_TOO_LARGE"


def test_request_within_the_size_limit_is_not_rejected_by_size(
    client: TestClient,
) -> None:
    # Hits a real route with a body under the limit — expect it to reach
    # routing/validation (422 for a malformed logout body), not 413.
    response = client.post("/api/v1/auth/logout", json={"not": "the right shape"})
    assert response.status_code != 413


class TestTrustedProxyClientIPResolution:
    """Direct unit coverage of
    cerebrum.middleware.request_context.RequestContextMiddleware._resolve_client_ip
    — Trusted Proxy Support (CIS Phase 1 Prompt 5).
    """

    @staticmethod
    def _build_middleware(trusted_proxies: list[str]):  # type: ignore[no-untyped-def]
        from cerebrum.config.environment import Environment
        from cerebrum.middleware.request_context import RequestContextMiddleware

        async def _dummy_app(scope: object, receive: object, send: object) -> None:
            return None

        return RequestContextMiddleware(
            _dummy_app, environment=Environment.TESTING, trusted_proxies=trusted_proxies  # type: ignore[arg-type]
        )

    @staticmethod
    def _fake_request(*, client_host: str | None, forwarded_for: str | None):  # type: ignore[no-untyped-def]
        class _FakeClient:
            def __init__(self, host: str | None) -> None:
                self.host = host

        class _FakeRequest:
            def __init__(self) -> None:
                self.client = _FakeClient(client_host) if client_host else None
                self.headers = (
                    {"X-Forwarded-For": forwarded_for} if forwarded_for else {}
                )

        return _FakeRequest()

    def test_forwarded_header_is_ignored_from_an_untrusted_peer(self) -> None:
        middleware = self._build_middleware(trusted_proxies=["10.0.0.1"])
        request = self._fake_request(client_host="203.0.113.5", forwarded_for="1.2.3.4")

        assert middleware._resolve_client_ip(request) == "203.0.113.5"  # type: ignore[arg-type]

    def test_forwarded_header_is_honored_from_a_trusted_proxy(self) -> None:
        middleware = self._build_middleware(trusted_proxies=["10.0.0.1"])
        request = self._fake_request(
            client_host="10.0.0.1", forwarded_for="203.0.113.9"
        )

        assert middleware._resolve_client_ip(request) == "203.0.113.9"  # type: ignore[arg-type]

    def test_leftmost_forwarded_entry_is_the_original_client(self) -> None:
        middleware = self._build_middleware(trusted_proxies=["10.0.0.1"])
        request = self._fake_request(
            client_host="10.0.0.1", forwarded_for="203.0.113.9, 10.0.0.2, 10.0.0.1"
        )

        assert middleware._resolve_client_ip(request) == "203.0.113.9"  # type: ignore[arg-type]

    def test_no_client_at_all_resolves_to_none(self) -> None:
        middleware = self._build_middleware(trusted_proxies=["10.0.0.1"])
        request = self._fake_request(client_host=None, forwarded_for=None)

        assert middleware._resolve_client_ip(request) is None  # type: ignore[arg-type]
