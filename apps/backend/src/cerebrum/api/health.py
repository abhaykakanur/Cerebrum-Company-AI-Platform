"""Liveness, readiness, and detailed health endpoints.

See docs/architecture/specification/38_Observability.md's Health Checks
table. Registered at the application root (not under ``/api/v1``) since
these are process-orchestration signals, not versioned business API
surface — see CIS Phase 1 Prompt 3 Section 3's API Foundation list, which
names ``/health``, ``/live``, ``/ready`` alongside, not beneath, ``/api/v1``.

Detailed status (CIS Phase 1 Prompt 4) is read directly from each
infrastructure client manager on :class:`~cerebrum.core.state.ApplicationState`
— this module adapts
:class:`~cerebrum.infrastructure.health.ComponentHealth` (the
infrastructure layer's internal shape) into
:class:`~cerebrum.api.schemas.health.ComponentStatus` (this layer's HTTP
response shape); infrastructure/ itself never imports api/, per
docs/architecture/dependency-rules.md.
"""

import asyncio
from typing import Literal

from fastapi import APIRouter

from cerebrum.api.schemas.health import (
    ComponentStatus,
    HealthResponse,
    LivenessResponse,
    ReadinessResponse,
)
from cerebrum.core.state import ApplicationState
from cerebrum.dependencies.state import ApplicationStateDep
from cerebrum.infrastructure.health import ComponentHealth
from cerebrum.utils.clock import utcnow

router = APIRouter(tags=["Health"])


async def _gather_component_health(state: ApplicationState) -> list[ComponentHealth]:
    results = await asyncio.gather(
        state.database.health_check(),
        state.neo4j.health_check(),
        state.redis.health_check(),
        state.qdrant.health_check(),
        state.minio.health_check(),
        state.opensearch.health_check(),
    )
    return list(results)


@router.get("/live", response_model=LivenessResponse)
async def liveness() -> LivenessResponse:
    """Is this process running and not deadlocked? No dependency check —
    a slow database must not fail liveness, only readiness.
    """
    return LivenessResponse()


@router.get("/ready", response_model=ReadinessResponse)
async def readiness(state: ApplicationStateDep) -> ReadinessResponse:
    """Can this process currently serve traffic? Gated on PostgreSQL
    specifically — the authoritative relational datastore every future
    domain depends on — rather than requiring all six clients healthy: a
    momentarily-unreachable OpenSearch or Qdrant (not yet used by
    anything) should not pull this process out of load-balancer rotation.
    """
    postgres_health = await state.database.health_check()
    is_ready = postgres_health.status == "healthy"
    return ReadinessResponse(status="ready" if is_ready else "not_ready")


@router.get("/health", response_model=HealthResponse)
async def health(state: ApplicationStateDep) -> HealthResponse:
    """The detailed, per-subsystem status surfaced to a monitoring
    dashboard — does not itself drive an orchestrator action.
    """
    component_health = await _gather_component_health(state)
    components = [
        ComponentStatus(name=c.name, status=c.status, detail=c.detail)
        for c in component_health
    ]
    healthy_count = sum(1 for c in component_health if c.status == "healthy")
    overall_status: Literal["healthy", "degraded", "unhealthy"]
    if healthy_count == len(component_health):
        overall_status = "healthy"
    elif healthy_count == 0:
        overall_status = "unhealthy"
    else:
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        version=state.settings.application.version,
        environment=state.settings.application.environment.value,
        uptime_seconds=state.uptime_seconds,
        timestamp=utcnow(),
        components=components,
    )
