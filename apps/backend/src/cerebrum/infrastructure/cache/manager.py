"""``RedisClientManager``: connection lifecycle for Redis."""

from time import perf_counter

import redis.asyncio as redis_asyncio
from structlog.typing import FilteringBoundLogger

from cerebrum.config.infrastructure import InfrastructureSettings
from cerebrum.config.redis import RedisSettings
from cerebrum.infrastructure.health import ComponentHealth
from cerebrum.infrastructure.retry import connect_with_retry
from cerebrum.shared.errors.exceptions import InfrastructureException

_COMPONENT_NAME = "redis"


class RedisClientManager:
    """Owns a pooled ``redis.asyncio.Redis`` client."""

    def __init__(
        self,
        settings: RedisSettings,
        infra_settings: InfrastructureSettings,
        logger: FilteringBoundLogger,
    ) -> None:
        self._settings = settings
        self._infra_settings = infra_settings
        self._logger = logger
        self._client: redis_asyncio.Redis | None = None

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    @property
    def client(self) -> redis_asyncio.Redis:
        if self._client is None:
            raise InfrastructureException(f"{_COMPONENT_NAME} is not connected.")
        return self._client

    async def connect(self) -> None:
        async def _attempt() -> redis_asyncio.Redis:
            client: redis_asyncio.Redis = redis_asyncio.from_url(
                self._settings.dsn,
                socket_connect_timeout=self._infra_settings.connect_timeout_seconds,
                socket_timeout=self._infra_settings.connect_timeout_seconds,
            )
            try:
                await client.ping()
            except Exception:
                await client.aclose()
                raise
            return client

        client = await connect_with_retry(
            component=_COMPONENT_NAME,
            attempt=_attempt,
            settings=self._infra_settings,
            logger=self._logger,
        )
        if client is not None:
            self._client = client
            self._logger.info("infrastructure.connected", component=_COMPONENT_NAME)

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            self._logger.info("infrastructure.disconnected", component=_COMPONENT_NAME)

    async def health_check(self) -> ComponentHealth:
        if self._client is None:
            return ComponentHealth(name=_COMPONENT_NAME, status="unavailable")
        start = perf_counter()
        try:
            await self._client.ping()
        except Exception as exc:
            return ComponentHealth(
                name=_COMPONENT_NAME, status="unavailable", detail=str(exc)
            )
        return ComponentHealth(
            name=_COMPONENT_NAME,
            status="healthy",
            latency_ms=(perf_counter() - start) * 1000,
        )
