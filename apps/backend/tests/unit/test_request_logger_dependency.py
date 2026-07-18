"""Proves CIS Phase 1 Prompt 7's Testing improvement: the Logger
dependency provider (cerebrum.dependencies.logging) — real, working
code with zero direct test coverage — correctly binds Request ID/
Correlation ID onto the returned logger when a
:class:`~cerebrum.middleware.context.RequestContext` is present, and
degrades gracefully (an unbound logger, not an error) when it is not.
"""

from types import SimpleNamespace

import pytest

from cerebrum.dependencies.logging import get_request_logger
from cerebrum.middleware.context import RequestContext

pytestmark = pytest.mark.unit


def test_returns_a_logger_when_no_request_context_is_bound() -> None:
    request = SimpleNamespace(state=SimpleNamespace())
    logger = get_request_logger(request)  # type: ignore[arg-type]
    assert logger is not None


def test_binds_request_id_and_correlation_id_when_context_is_present() -> None:
    context = RequestContext(
        request_id="req-1",
        correlation_id="corr-1",
        method="GET",
        path="/x",
        client_ip=None,
        user_agent=None,
        environment="testing",
    )
    request = SimpleNamespace(state=SimpleNamespace(cerebrum_context=context))

    logger = get_request_logger(request)  # type: ignore[arg-type]

    bound_context = logger._context  # type: ignore[attr-defined]
    assert bound_context["request_id"] == "req-1"
    assert bound_context["correlation_id"] == "corr-1"
