"""The typed :class:`RequestContext` every HTTP request owns exactly one
of, and the contextvar that makes it available anywhere in the call
stack — logging, exception handlers, future application services —
without threading it through every function signature.

See CIS Phase 1 Prompt 3 Section 3's Request Context requirement. Tenant,
Workspace, and Authenticated User are typed as ``None``-defaulted
placeholders: no Authentication or Multi-Tenancy domain exists yet (see
this milestone's Non-Objectives), but the field names are fixed now so
those future domains populate an existing contract rather than one
introduced alongside them.
"""

from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from datetime import datetime

from cerebrum.utils.clock import utcnow


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
