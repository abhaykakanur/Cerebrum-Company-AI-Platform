"""Proves the acceptance criterion "Exception handling is centralized"
from CIS Phase 1 Prompt 3, and
docs/architecture/specification/38_Observability.md's Error Taxonomy.
"""

import pytest
from fastapi.testclient import TestClient

from cerebrum.shared.errors.base import ErrorCategory, ErrorSeverity
from cerebrum.shared.errors.exceptions import (
    ConfigurationException,
    InfrastructureException,
    ValidationException,
)

pytestmark = pytest.mark.unit


def test_validation_exception_defaults() -> None:
    exc = ValidationException("bad input")
    assert exc.category == ErrorCategory.VALIDATION
    assert exc.http_status == 422
    assert exc.severity == ErrorSeverity.LOW
    assert exc.retryable is False


def test_configuration_exception_is_never_retryable() -> None:
    exc = ConfigurationException("missing value")
    assert exc.category == ErrorCategory.CONFIGURATION
    assert exc.retryable is False
    assert exc.severity == ErrorSeverity.CRITICAL


def test_infrastructure_exception_defaults_to_retryable() -> None:
    exc = InfrastructureException("connection refused")
    assert exc.category == ErrorCategory.INFRASTRUCTURE
    assert exc.retryable is True


def test_exception_preserves_cause_chain() -> None:
    original = ValueError("root cause")
    exc = ValidationException("wrapped", cause=original)
    assert exc.__cause__ is original


def test_unmatched_route_returns_standard_error_envelope(client: TestClient) -> None:
    response = client.get("/this-route-does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error_code"] == "HTTP_404"
    assert "request_id" in body
    assert "timestamp" in body
    assert "version" in body
