"""``OpenSearchClientManager``: connection lifecycle for OpenSearch."""

from time import perf_counter
from typing import cast

from opensearchpy import AsyncOpenSearch
from structlog.typing import FilteringBoundLogger

from cerebrum.config.infrastructure import InfrastructureSettings
from cerebrum.config.opensearch import OpenSearchSettings
from cerebrum.infrastructure.health import ComponentHealth
from cerebrum.infrastructure.retry import connect_with_retry
from cerebrum.shared.errors.exceptions import InfrastructureException

_COMPONENT_NAME = "opensearch"


class OpenSearchClientManager:
    """Owns an ``AsyncOpenSearch`` client."""

    def __init__(
        self,
        settings: OpenSearchSettings,
        infra_settings: InfrastructureSettings,
        logger: FilteringBoundLogger,
    ) -> None:
        self._settings = settings
        self._infra_settings = infra_settings
        self._logger = logger
        self._client: AsyncOpenSearch | None = None

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    @property
    def client(self) -> AsyncOpenSearch:
        if self._client is None:
            raise InfrastructureException(f"{_COMPONENT_NAME} is not connected.")
        return self._client

    async def connect(self) -> None:
        async def _attempt() -> AsyncOpenSearch:
            client = AsyncOpenSearch(
                hosts=[{"host": self._settings.host, "port": self._settings.port}],
                use_ssl=False,
                verify_certs=False,
                timeout=self._infra_settings.connect_timeout_seconds,
            )
            try:
                if not await client.ping():
                    raise InfrastructureException(f"{_COMPONENT_NAME} ping failed.")
            except Exception:
                # A failed attempt still opened an aiohttp session — close
                # it before propagating, or it leaks (a ResourceWarning
                # from aiohttp) once this local ``client`` goes out of
                # scope, since nothing else holds a reference to close it.
                await client.close()
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
            await self._client.close()
            self._client = None
            self._logger.info("infrastructure.disconnected", component=_COMPONENT_NAME)

    async def health_check(self) -> ComponentHealth:
        if self._client is None:
            return ComponentHealth(name=_COMPONENT_NAME, status="unavailable")
        start = perf_counter()
        try:
            healthy = cast(bool, await self._client.ping())
        except Exception as exc:
            return ComponentHealth(
                name=_COMPONENT_NAME, status="unavailable", detail=str(exc)
            )
        if not healthy:
            return ComponentHealth(
                name=_COMPONENT_NAME,
                status="unavailable",
                detail="Ping returned false.",
            )
        return ComponentHealth(
            name=_COMPONENT_NAME,
            status="healthy",
            latency_ms=(perf_counter() - start) * 1000,
        )
