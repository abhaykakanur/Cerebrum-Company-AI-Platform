"""``MinIOClientManager``: connection lifecycle for MinIO."""

import asyncio
from time import perf_counter

import urllib3
from minio import Minio
from structlog.typing import FilteringBoundLogger

from cerebrum.config.infrastructure import InfrastructureSettings
from cerebrum.config.minio import MinIOSettings
from cerebrum.infrastructure.health import ComponentHealth
from cerebrum.infrastructure.retry import connect_with_retry
from cerebrum.shared.errors.exceptions import InfrastructureException

_COMPONENT_NAME = "minio"


class MinIOClientManager:
    """Owns a ``Minio`` client and validates the configured bucket exists.

    The official SDK is synchronous; every call is dispatched via
    ``asyncio.to_thread`` so callers never block the event loop.
    """

    def __init__(
        self,
        settings: MinIOSettings,
        infra_settings: InfrastructureSettings,
        logger: FilteringBoundLogger,
    ) -> None:
        self._settings = settings
        self._infra_settings = infra_settings
        self._logger = logger
        self._client: Minio | None = None

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    @property
    def client(self) -> Minio:
        if self._client is None:
            raise InfrastructureException(f"{_COMPONENT_NAME} is not connected.")
        return self._client

    def _build_http_client(self) -> urllib3.PoolManager:
        """The official SDK's default ``http_client`` has no connect/read
        timeout, so an unreachable or packet-dropping host hangs
        indefinitely rather than raising — bounding it here is what
        makes :class:`~cerebrum.config.infrastructure.InfrastructureSettings`'s
        ``connect_timeout_seconds`` actually take effect for MinIO.
        """
        timeout = urllib3.Timeout(
            connect=self._infra_settings.connect_timeout_seconds,
            read=self._infra_settings.connect_timeout_seconds,
        )
        return urllib3.PoolManager(timeout=timeout, retries=False)

    async def connect(self) -> None:
        async def _attempt() -> Minio:
            client = Minio(
                self._settings.endpoint,
                access_key=self._settings.access_key,
                secret_key=self._settings.secret_key.get_secret_value(),
                secure=self._settings.secure,
                http_client=self._build_http_client(),
            )
            bucket = self._settings.bucket
            exists = await asyncio.to_thread(client.bucket_exists, bucket)
            if not exists:
                await asyncio.to_thread(client.make_bucket, bucket)
                self._logger.info(
                    "infrastructure.bucket_created",
                    component=_COMPONENT_NAME,
                    bucket=bucket,
                )
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
        # The MinIO SDK holds no persistent connection to release (each
        # call is an independent HTTP request) — clearing the reference
        # is sufficient and keeps disconnect() symmetric with every other
        # manager's shape.
        if self._client is not None:
            self._client = None
            self._logger.info("infrastructure.disconnected", component=_COMPONENT_NAME)

    async def health_check(self) -> ComponentHealth:
        if self._client is None:
            return ComponentHealth(name=_COMPONENT_NAME, status="unavailable")
        start = perf_counter()
        try:
            await asyncio.to_thread(self._client.bucket_exists, self._settings.bucket)
        except Exception as exc:
            return ComponentHealth(
                name=_COMPONENT_NAME, status="unavailable", detail=str(exc)
            )
        return ComponentHealth(
            name=_COMPONENT_NAME,
            status="healthy",
            latency_ms=(perf_counter() - start) * 1000,
        )
