"""Infrastructure client dependency providers.

Every provider reads its client manager off
:class:`~cerebrum.core.state.ApplicationState` and returns the manager's
underlying client — raising
:class:`~cerebrum.shared.errors.exceptions.InfrastructureException` if
that client failed to connect at startup (see
cerebrum.core.lifecycle), rather than returning ``None`` and letting a
confusing ``AttributeError`` surface deeper in a route handler. All are
"Singleton" lifetime — the same client object, for the life of the
process. PostgreSQL is the one exception: see
``cerebrum.dependencies.database.DbSessionDep`` for its "Scoped"
per-request ``AsyncSession`` dependency instead of a raw client here.
"""

from typing import Annotated

from fastapi import Depends
from minio import Minio
from neo4j import AsyncDriver
from opensearchpy import AsyncOpenSearch
from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis

from cerebrum.core.observability import MetricsRegistry, Tracer
from cerebrum.dependencies.state import ApplicationStateDep


def get_redis(state: ApplicationStateDep) -> Redis:
    return state.redis.client


def get_neo4j(state: ApplicationStateDep) -> AsyncDriver:
    return state.neo4j.client


def get_qdrant(state: ApplicationStateDep) -> AsyncQdrantClient:
    return state.qdrant.client


def get_minio(state: ApplicationStateDep) -> Minio:
    return state.minio.client


def get_opensearch(state: ApplicationStateDep) -> AsyncOpenSearch:
    return state.opensearch.client


def get_metrics_registry(state: ApplicationStateDep) -> MetricsRegistry:
    return state.metrics


def get_tracer(state: ApplicationStateDep) -> Tracer:
    return state.tracer


RedisDep = Annotated[Redis, Depends(get_redis)]
Neo4jDep = Annotated[AsyncDriver, Depends(get_neo4j)]
QdrantDep = Annotated[AsyncQdrantClient, Depends(get_qdrant)]
MinIODep = Annotated[Minio, Depends(get_minio)]
OpenSearchDep = Annotated[AsyncOpenSearch, Depends(get_opensearch)]
MetricsRegistryDep = Annotated[MetricsRegistry, Depends(get_metrics_registry)]
TracerDep = Annotated[Tracer, Depends(get_tracer)]
