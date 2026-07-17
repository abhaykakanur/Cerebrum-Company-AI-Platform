"""The shared health-reporting contract every infrastructure client
manager implements.

Deliberately defined here rather than reused from ``api.schemas.health``
— the presentation layer's response shape is allowed to depend on this
module (api/ may import infrastructure/), but infrastructure/ must never
import api/, per docs/architecture/dependency-rules.md's Cross-Cutting
Layers note. cerebrum.api.health adapts :class:`ComponentHealth` into its
own response schema.
"""

from dataclasses import dataclass
from typing import Literal, Protocol

ComponentHealthStatus = Literal["healthy", "degraded", "unavailable", "not_configured"]


@dataclass(frozen=True, slots=True)
class ComponentHealth:
    """One infrastructure client's current status."""

    name: str
    status: ComponentHealthStatus
    detail: str | None = None
    latency_ms: float | None = None


class InfrastructureClientManager(Protocol):
    """Every client manager in cerebrum.infrastructure (PostgreSQL,
    Redis, Neo4j, Qdrant, MinIO, OpenSearch) implements this shape,
    letting cerebrum.api.health iterate over all six uniformly rather
    than special-casing each technology.
    """

    @property
    def is_connected(self) -> bool: ...

    async def connect(self) -> None:
        """Establishes the connection, retrying per
        :class:`~cerebrum.config.infrastructure.InfrastructureSettings`.
        Never raises — a failure leaves :attr:`is_connected` ``False``
        and is reported through :meth:`health_check`, per CIS Phase 1
        Prompt 4's "never leak driver exceptions" rule.
        """
        ...

    async def disconnect(self) -> None:
        """Releases the connection. Idempotent — safe to call even if
        :meth:`connect` was never called or already failed.
        """
        ...

    async def health_check(self) -> ComponentHealth: ...
