"""Health, liveness, and readiness response shapes.

See docs/architecture/specification/38_Observability.md's Health Checks
table: three distinct check types with distinct failure semantics.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from cerebrum.utils.clock import utcnow

ComponentStatusValue = Literal["healthy", "degraded", "unavailable", "not_configured"]


class ComponentStatus(BaseModel):
    """One subsystem's contribution to the aggregate detailed-health
    status — see docs/architecture/specification/38_Observability.md
    ("Every one of the fifteen high-level components ... that has an
    external dependency ... contributes to the detailed Health check's
    aggregate status"). ``not_configured`` is this milestone's status for
    every datastore, since no client is established yet.
    """

    name: str
    status: ComponentStatusValue
    detail: str | None = None


class HealthResponse(BaseModel):
    """``GET /health`` — the detailed check, surfaced to a dashboard, not
    acted on directly by an orchestrator.
    """

    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    environment: str
    uptime_seconds: float
    timestamp: datetime = Field(default_factory=utcnow)
    components: list[ComponentStatus]


class LivenessResponse(BaseModel):
    """``GET /live`` — process is running and not deadlocked. Failure
    triggers an orchestrator restart.
    """

    status: Literal["alive"] = "alive"
    timestamp: datetime = Field(default_factory=utcnow)


class ReadinessResponse(BaseModel):
    """``GET /ready`` — process can currently serve traffic. Failure
    removes it from load-balancer rotation without a restart.
    """

    status: Literal["ready", "not_ready"]
    timestamp: datetime = Field(default_factory=utcnow)
