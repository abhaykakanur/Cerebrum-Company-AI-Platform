"""Proves the acceptance criteria "Sessions close correctly" and the
"Connection lifecycle"/"Health checks" testing requirements from CIS
Phase 1 Prompt 4 for every one of the six client managers.

Deliberately does not reuse the ambient ``settings`` fixture's real
``localhost`` datastore configuration — a developer who has run
``scripts/start.sh`` first would have real infrastructure listening on
those exact ports, making "is this manager disconnected" a flaky
assertion. Every manager here is instead pointed at port 1 — a port no
real service binds to — so "connection refused" is deterministic
regardless of what else is running on the machine. See CIS Phase 1
Prompt 4's "Mock support" testing requirement.
"""

import pytest
import structlog

from cerebrum.config.database import PostgresSettings
from cerebrum.config.infrastructure import InfrastructureSettings
from cerebrum.config.minio import MinIOSettings
from cerebrum.config.neo4j import Neo4jSettings
from cerebrum.config.opensearch import OpenSearchSettings
from cerebrum.config.qdrant import QdrantSettings
from cerebrum.config.redis import RedisSettings
from cerebrum.infrastructure.cache.manager import RedisClientManager
from cerebrum.infrastructure.database.manager import PostgresClientManager
from cerebrum.infrastructure.graph.manager import Neo4jClientManager
from cerebrum.infrastructure.search.manager import OpenSearchClientManager
from cerebrum.infrastructure.storage.manager import MinIOClientManager
from cerebrum.infrastructure.vector.manager import QdrantClientManager
from cerebrum.shared.errors.exceptions import InfrastructureException

pytestmark = pytest.mark.unit

_logger = structlog.get_logger()
_UNREACHABLE_HOST = "127.0.0.1"
_UNREACHABLE_PORT = 1  # a port no real service binds to.
_FAST_INFRA_SETTINGS = InfrastructureSettings(
    connect_retries=0, connect_retry_backoff_seconds=0.01, connect_timeout_seconds=1.0
)

_MANAGER_FACTORIES = {
    "postgres": lambda: PostgresClientManager(
        PostgresSettings(host=_UNREACHABLE_HOST, port=_UNREACHABLE_PORT),
        _FAST_INFRA_SETTINGS,
        _logger,
    ),
    "redis": lambda: RedisClientManager(
        RedisSettings(host=_UNREACHABLE_HOST, port=_UNREACHABLE_PORT),
        _FAST_INFRA_SETTINGS,
        _logger,
    ),
    "neo4j": lambda: Neo4jClientManager(
        Neo4jSettings(host=_UNREACHABLE_HOST, port=_UNREACHABLE_PORT),
        _FAST_INFRA_SETTINGS,
        _logger,
    ),
    "qdrant": lambda: QdrantClientManager(
        QdrantSettings(host=_UNREACHABLE_HOST, port=_UNREACHABLE_PORT),
        _FAST_INFRA_SETTINGS,
        _logger,
    ),
    "minio": lambda: MinIOClientManager(
        MinIOSettings(endpoint=f"{_UNREACHABLE_HOST}:{_UNREACHABLE_PORT}"),
        _FAST_INFRA_SETTINGS,
        _logger,
    ),
    "opensearch": lambda: OpenSearchClientManager(
        OpenSearchSettings(host=_UNREACHABLE_HOST, port=_UNREACHABLE_PORT),
        _FAST_INFRA_SETTINGS,
        _logger,
    ),
}


@pytest.fixture(params=list(_MANAGER_FACTORIES), ids=list(_MANAGER_FACTORIES))
def manager(request: pytest.FixtureRequest):  # type: ignore[no-untyped-def]
    return _MANAGER_FACTORIES[request.param]()


def test_starts_disconnected(manager) -> None:  # type: ignore[no-untyped-def]
    assert manager.is_connected is False


async def test_health_check_reports_unavailable_before_connect(manager) -> None:  # type: ignore[no-untyped-def]
    health = await manager.health_check()
    assert health.status == "unavailable"


async def test_disconnect_before_connect_is_a_safe_noop(manager) -> None:  # type: ignore[no-untyped-def]
    await manager.disconnect()  # must not raise
    assert manager.is_connected is False


async def test_connect_against_unreachable_service_leaves_disconnected(manager) -> None:  # type: ignore[no-untyped-def]
    await manager.connect()  # never raises — see cerebrum.infrastructure.health
    assert manager.is_connected is False


def test_client_access_before_connect_raises(manager) -> None:  # type: ignore[no-untyped-def]
    # Checked on the class, not the instance: the ``.client`` property
    # itself raises on access while disconnected, so `hasattr(manager,
    # "client")` would propagate that exception rather than returning
    # False (hasattr only swallows AttributeError, per Python 3 semantics).
    if not hasattr(type(manager), "client"):
        pytest.skip("this manager exposes session_factory instead of .client")
    with pytest.raises(InfrastructureException):
        _ = manager.client


def test_postgres_session_factory_access_before_connect_raises() -> None:
    manager = _MANAGER_FACTORIES["postgres"]()
    with pytest.raises(InfrastructureException):
        _ = manager.session_factory
