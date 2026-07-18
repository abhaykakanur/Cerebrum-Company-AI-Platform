"""API Metrics and Tracing (CIS Phase 1 Prompt 6, extended by CIS Phase 1
Prompt 7's Observability Review): records Latency, Request Count, Status
Codes, Endpoint Usage, and Response Size through the
:class:`~cerebrum.core.observability.MetricsRegistry` port, and opens one
per-request span through the :class:`~cerebrum.core.observability.Tracer`
port. Every call is a no-op today
(:class:`~cerebrum.core.observability.NoOpMetricsRegistry`/
:class:`~cerebrum.core.observability.NoOpTracer`) — this middleware
exists so both sets of recording points are correct and already wired in
before a real backend (Prometheus/OpenTelemetry) is registered on
:class:`~cerebrum.core.state.ApplicationState`, per that module's
docstring. See
docs/architecture/specification/81_API_Standards.md's Observability
section. Kept as one middleware, not two, since both concerns instrument
the exact same request boundary — see docs/architecture/coding-guidelines.md's
"No Premature Abstraction".

Reads ``request.app.state.cerebrum`` directly rather than receiving it as
a constructor argument: unlike cerebrum.middleware.authentication's
``token_service`` (cheap, stateless, buildable at app-construction time),
the real :class:`~cerebrum.core.state.ApplicationState` is only assembled
inside cerebrum.core.lifecycle's lifespan context manager, which runs
after every middleware is already registered — this is the same
per-request-read pattern cerebrum.dependencies.state.get_application_state
uses, adapted for middleware (which cannot depend on a FastAPI
dependency the way a route can).

Must run inner to (registered before) RequestContextMiddleware, whose
:class:`~cerebrum.middleware.context.RequestContext` supplies
``elapsed_ms`` — see cerebrum.middleware.registry.
"""

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class APIMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        tracer = request.app.state.cerebrum.tracer
        with tracer.start_span(f"{request.method} {request.url.path}"):
            response = await call_next(request)

        metrics = request.app.state.cerebrum.metrics
        route = request.scope.get("route")
        endpoint = getattr(route, "path", request.url.path)
        labels = {
            "method": request.method,
            "endpoint": endpoint,
            "status_code": str(response.status_code),
        }

        metrics.increment_counter("api_requests_total", labels=labels)

        context = getattr(request.state, "cerebrum_context", None)
        if context is not None:
            metrics.observe_histogram(
                "api_request_duration_ms", context.elapsed_ms, labels=labels
            )

        content_length = response.headers.get("content-length")
        if content_length is not None:
            metrics.observe_histogram(
                "api_response_size_bytes", float(content_length), labels=labels
            )

        return response
