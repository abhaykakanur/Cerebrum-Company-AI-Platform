"""Builds the request's :class:`~cerebrum.middleware.context.RequestContext`
from the identifiers RequestIDMiddleware and CorrelationIDMiddleware
already attached to ``request.state``, then binds it to the contextvar
for the duration of the request.

Must run after RequestIDMiddleware, CorrelationIDMiddleware, and (as of
CIS Phase 1 Prompt 5) AuthenticationMiddleware, and before
RequestTimingMiddleware/StructuredLoggingMiddleware — see
cerebrum.middleware.registry for the enforced order.
"""

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from cerebrum.config.environment import Environment
from cerebrum.middleware.context import (
    AuthIdentity,
    RequestContext,
    bind_request_context,
    reset_request_context,
)

_WORKSPACE_HEADER = "X-Workspace-ID"
_FORWARDED_FOR_HEADER = "X-Forwarded-For"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assembles and binds the per-request :class:`RequestContext`."""

    def __init__(
        self, app: ASGIApp, *, environment: Environment, trusted_proxies: list[str]
    ) -> None:
        super().__init__(app)
        self._environment = environment
        self._trusted_proxies = frozenset(trusted_proxies)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        auth_identity: AuthIdentity | None = getattr(
            request.state, "auth_identity", None
        )

        context = RequestContext(
            request_id=request.state.request_id,
            correlation_id=request.state.correlation_id,
            method=request.method,
            path=request.url.path,
            client_ip=self._resolve_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
            environment=self._environment.value,
            tenant_id=str(auth_identity.organization_id) if auth_identity else None,
            workspace_id=request.headers.get(_WORKSPACE_HEADER),
            authenticated_user_id=str(auth_identity.user_id) if auth_identity else None,
        )
        request.state.cerebrum_context = context
        token = bind_request_context(context)
        try:
            return await call_next(request)
        finally:
            reset_request_context(token)

    def _resolve_client_ip(self, request: Request) -> str | None:
        """Trusted Proxy Support: the socket's peer address is trusted
        by definition (it's who actually connected to us); ``X-Forwarded-For``
        is trusted only when that peer is itself a configured trusted
        proxy (``SecuritySettings.trusted_proxies``) — otherwise any
        client could forge the header to spoof its own IP in audit logs
        and rate limiting. The header's leftmost entry is the original
        client, per the standard ``X-Forwarded-For: client, proxy1,
        proxy2`` convention.
        """
        direct_ip = request.client.host if request.client else None
        if direct_ip is None or direct_ip not in self._trusted_proxies:
            return direct_ip

        forwarded_for = request.headers.get(_FORWARDED_FOR_HEADER)
        if not forwarded_for:
            return direct_ip
        return forwarded_for.split(",")[0].strip() or direct_ip
