"""The Application Lifecycle: Startup → Initialization → Dependency
Validation → Infrastructure Validation → Ready → Serving Requests →
Shutdown → Cleanup → Resource Disposal, per CIS Phase 1 Prompt 3 Section
2. Implemented as a single FastAPI ``lifespan`` async context manager —
the one place async resource acquisition and release happens, distinct
from the Application Factory's synchronous registration steps (see
cerebrum.core.factory), which run once at construction time regardless
of whether the process ever actually serves a request (e.g. under
``pytest``, TestClient construction alone never enters this function
unless used as a context manager).

Infrastructure Validation (CIS Phase 1 Prompt 4) connects all six
datastore clients concurrently. A client that fails to connect (after
its configured retries — see
cerebrum.config.infrastructure.InfrastructureSettings) does not fail
startup: it is left disconnected, reported as ``unavailable`` by
cerebrum.api.health, and usable again once the underlying service
recovers — no restart required. This mirrors the Readiness Check
semantics in docs/architecture/specification/38_Observability.md
("failure removes it from load-balancer rotation without restarting").
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from cerebrum.config.settings import Settings
from cerebrum.core.logging import get_logger
from cerebrum.core.observability import NoOpMetricsRegistry, NoOpTracer
from cerebrum.core.state import ApplicationState
from cerebrum.infrastructure.cache.manager import RedisClientManager
from cerebrum.infrastructure.database.manager import PostgresClientManager
from cerebrum.infrastructure.graph.manager import Neo4jClientManager
from cerebrum.infrastructure.search.manager import OpenSearchClientManager
from cerebrum.infrastructure.storage.manager import MinIOClientManager
from cerebrum.infrastructure.vector.manager import QdrantClientManager

_logger = get_logger("cerebrum.core")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.cerebrum_settings
    _logger.info("startup.begin", environment=settings.application.environment.value)

    infra_logger = get_logger("cerebrum.infrastructure")
    state = ApplicationState(
        settings=settings,
        metrics=NoOpMetricsRegistry(),
        tracer=NoOpTracer(),
        database=PostgresClientManager(
            settings.postgres, settings.infrastructure, infra_logger
        ),
        redis=RedisClientManager(settings.redis, settings.infrastructure, infra_logger),
        neo4j=Neo4jClientManager(settings.neo4j, settings.infrastructure, infra_logger),
        qdrant=QdrantClientManager(
            settings.qdrant, settings.infrastructure, infra_logger
        ),
        minio=MinIOClientManager(settings.minio, settings.infrastructure, infra_logger),
        opensearch=OpenSearchClientManager(
            settings.opensearch, settings.infrastructure, infra_logger
        ),
    )
    app.state.cerebrum = state
    _logger.info("startup.state_initialized")

    # Infrastructure Validation: connect every client concurrently. Each
    # manager's connect() never raises (see
    # cerebrum.infrastructure.health.InfrastructureClientManager) — a
    # connection failure is reflected in that manager's is_connected
    # property, not an exception here.
    await asyncio.gather(
        state.database.connect(),
        state.redis.connect(),
        state.neo4j.connect(),
        state.qdrant.connect(),
        state.minio.connect(),
        state.opensearch.connect(),
    )
    connected = [
        name
        for name, manager in (
            ("postgresql", state.database),
            ("redis", state.redis),
            ("neo4j", state.neo4j),
            ("qdrant", state.qdrant),
            ("minio", state.minio),
            ("opensearch", state.opensearch),
        )
        if manager.is_connected
    ]
    _logger.info(
        "startup.infrastructure_validated",
        connected=connected,
        unavailable=[
            name
            for name in (
                "postgresql",
                "redis",
                "neo4j",
                "qdrant",
                "minio",
                "opensearch",
            )
            if name not in connected
        ],
    )

    _logger.info("startup.complete")
    yield

    _logger.info("shutdown.begin")
    # Reverse-order cleanup: Workers -> Background Runtime ->
    # Infrastructure Clients -> Logger Flush -> Dispose Resources.
    _logger.info("shutdown.workers_stopped", reason="No worker runtime was started.")
    await asyncio.gather(
        state.database.disconnect(),
        state.redis.disconnect(),
        state.neo4j.disconnect(),
        state.qdrant.disconnect(),
        state.minio.disconnect(),
        state.opensearch.disconnect(),
    )
    _logger.info("shutdown.infrastructure_clients_closed")
    _logger.info("shutdown.complete")
