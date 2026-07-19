"""The typed Application State every request-handling process holds
exactly one of.

See CIS Phase 1 Prompt 3 Section 2's Application State requirement. Every
infrastructure field holds a real client-manager instance from
cerebrum.infrastructure (see CIS Phase 1 Prompt 4) — construction is
cheap and does no I/O, so a manager always exists here; whether it
actually holds a live connection is tracked by its own ``is_connected``
property, set by cerebrum.core.lifecycle's startup/shutdown sequence.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

from cerebrum.config.settings import Settings
from cerebrum.core.observability import MetricsRegistry, Tracer
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.cache.manager import RedisClientManager
from cerebrum.infrastructure.database.manager import PostgresClientManager
from cerebrum.infrastructure.graph.manager import Neo4jClientManager
from cerebrum.infrastructure.search.manager import OpenSearchClientManager
from cerebrum.infrastructure.storage.manager import MinIOClientManager
from cerebrum.infrastructure.vector.manager import QdrantClientManager
from cerebrum.utils.clock import utcnow


@dataclass(slots=True)
class ApplicationState:
    """Attached to ``app.state.cerebrum`` during the lifespan's startup
    phase (see cerebrum.core.lifecycle) and read through the typed
    accessors in cerebrum.dependencies — never through raw ``app.state``
    attribute access outside of that one assignment point.
    """

    settings: Settings
    metrics: MetricsRegistry
    tracer: Tracer
    events: EventDispatcher
    database: PostgresClientManager
    redis: RedisClientManager
    neo4j: Neo4jClientManager
    qdrant: QdrantClientManager
    minio: MinIOClientManager
    opensearch: OpenSearchClientManager
    http_client: httpx.AsyncClient
    """A single pooled ``httpx.AsyncClient`` shared by every
    cerebrum.infrastructure.llm provider adapter that speaks HTTP
    (OpenAI/Anthropic/Gemini/Ollama) — see cerebrum.core.lifecycle for
    its construction/``aclose()``. Not an
    ``InfrastructureClientManager``: unlike the datastore clients above,
    opening an ``httpx.AsyncClient`` does no I/O and has no
    connect/retry semantics to track — it lazily opens connections per
    request.
    """
    started_at: datetime = field(default_factory=utcnow)

    # Background Processing Layer placeholder — see cerebrum.workers,
    # which defines interfaces only at this milestone.
    worker_manager: Any | None = None

    @property
    def uptime_seconds(self) -> float:
        return (utcnow() - self.started_at).total_seconds()
