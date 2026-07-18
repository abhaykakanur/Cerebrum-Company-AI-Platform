"""The typed :class:`RequestContext` every HTTP request owns exactly one
of, and the contextvar that makes it available anywhere in the call
stack — logging, exception handlers, application services — without
threading it through every function signature.

See CIS Phase 1 Prompt 3 Section 3's Request Context requirement. As of
CIS Phase 1 Prompt 5, ``tenant_id``/``authenticated_user_id`` are
populated from :class:`AuthIdentity` (resolved by
cerebrum.middleware.authentication.AuthenticationMiddleware, which runs
before cerebrum.middleware.request_context.RequestContextMiddleware —
see cerebrum.middleware.registry) for an authenticated request, and
remain ``None`` for an anonymous one. ``workspace_id`` is populated from
an optional ``X-Workspace-ID`` header, raw and unvalidated — see
docs/architecture/security/multi-tenancy-guide.md for why validating
that the caller actually belongs to that workspace is a route-dependency
concern (cerebrum.dependencies.auth), not this middleware's.
"""

import uuid
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from datetime import datetime

from starlette.requests import Request

from cerebrum.utils.clock import utcnow


@dataclass(frozen=True, slots=True)
class AuthIdentity:
    """The identity resolved from a valid access token or API key —
    everything :class:`RequestContext` and
    cerebrum.dependencies.auth.get_current_user need, without either
    re-decoding the token or loading the full
    :class:`~cerebrum.infrastructure.database.models.user.User` row
    just to know who's asking.
    """

    user_id: uuid.UUID
    organization_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Immutable snapshot of one HTTP request's identity and timing.

    Frozen because a request's identity must not change mid-flight;
    ``elapsed_ms`` is computed on demand from ``start_time`` rather than
    mutated, so the immutability holds even while the request is in
    flight.
    """

    request_id: str
    correlation_id: str
    method: str
    path: str
    client_ip: str | None
    user_agent: str | None
    environment: str
    start_time: datetime = field(default_factory=utcnow)

    tenant_id: str | None = None
    workspace_id: str | None = None
    authenticated_user_id: str | None = None

    @property
    def elapsed_ms(self) -> float:
        """Milliseconds elapsed since ``start_time``, evaluated fresh on
        every access rather than cached, since the request may still be
        in flight.
        """
        return (utcnow() - self.start_time).total_seconds() * 1000


_request_context_var: ContextVar[RequestContext | None] = ContextVar(
    "cerebrum_request_context", default=None
)


def get_current_request_context() -> RequestContext | None:
    """The active request's context, or ``None`` outside of a request
    (startup/shutdown code, a background Task not yet carrying a
    propagated context). Callers — chiefly logging and exception
    handling — must handle the ``None`` case explicitly rather than
    assume a request is always active.
    """
    return _request_context_var.get()


def bind_request_context(context: RequestContext) -> Token[RequestContext | None]:
    """Binds ``context`` to the current async task. Returns the token
    :func:`reset_request_context` needs to restore the previous value —
    callers (RequestContextMiddleware) SHALL always pair a bind with a
    reset in a ``finally`` block, so context never leaks across requests
    sharing an event loop.
    """
    return _request_context_var.set(context)


def reset_request_context(token: Token[RequestContext | None]) -> None:
    """Restores the contextvar to its pre-bind state. See
    :func:`bind_request_context`.
    """
    _request_context_var.reset(token)


def get_client_ip(request: Request) -> str | None:
    """The requesting client's IP address — the one shared implementation
    every "what IP made this request" call site (login rate limiting,
    general-purpose rate limiting, audit logging on login/refresh/logout)
    uses, rather than each reimplementing the same fallback (CIS Phase 1
    Prompt 7's duplicate-abstraction cleanup — three near-identical
    private copies previously existed in
    cerebrum.api.v1.auth/cerebrum.dependencies.auth/cerebrum.dependencies.rate_limit).

    Prefers the already-resolved :attr:`RequestContext.client_ip` (which
    accounts for Trusted Proxy Support — see
    cerebrum.middleware.request_context) when a context is bound, falling
    back to the raw ASGI-reported peer address for a caller that might
    run before ``RequestContextMiddleware`` has bound one.
    """
    context = get_current_request_context()
    if context is not None and context.client_ip is not None:
        return context.client_ip
    return request.client.host if request.client else None
