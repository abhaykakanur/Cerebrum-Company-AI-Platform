"""``Neo4jClientManager``: connection lifecycle for Neo4j."""

from time import perf_counter

from neo4j import AsyncDriver, AsyncGraphDatabase
from neo4j import AsyncSession as Neo4jAsyncSession
from structlog.typing import FilteringBoundLogger

from cerebrum.config.infrastructure import InfrastructureSettings
from cerebrum.config.neo4j import Neo4jSettings
from cerebrum.infrastructure.health import ComponentHealth
from cerebrum.infrastructure.retry import connect_with_retry
from cerebrum.shared.errors.exceptions import InfrastructureException

_COMPONENT_NAME = "neo4j"


class Neo4jClientManager:
    """Owns an ``AsyncDriver`` and provides scoped session creation."""

    def __init__(
        self,
        settings: Neo4jSettings,
        infra_settings: InfrastructureSettings,
        logger: FilteringBoundLogger,
    ) -> None:
        self._settings = settings
        self._infra_settings = infra_settings
        self._logger = logger
        self._driver: AsyncDriver | None = None

    @property
    def is_connected(self) -> bool:
        return self._driver is not None

    @property
    def client(self) -> AsyncDriver:
        """The raw driver — exposed alongside :meth:`session` so callers
        that only need ``driver.session()`` themselves (or symmetry with
        every other manager's ``.client`` property) don't have to reach
        into a private attribute.
        """
        if self._driver is None:
            raise InfrastructureException(f"{_COMPONENT_NAME} is not connected.")
        return self._driver

    def session(self) -> Neo4jAsyncSession:
        """A new Neo4j session, scoped to the caller's ``async with``
        block — mirrors the driver's own session-per-unit-of-work model.
        """
        if self._driver is None:
            raise InfrastructureException(f"{_COMPONENT_NAME} is not connected.")
        return self._driver.session()

    async def connect(self) -> None:
        async def _attempt() -> AsyncDriver:
            driver = AsyncGraphDatabase.driver(
                self._settings.bolt_uri,
                auth=(self._settings.user, self._settings.password.get_secret_value()),
                connection_timeout=self._infra_settings.connect_timeout_seconds,
            )
            try:
                await driver.verify_connectivity()
            except Exception:
                await driver.close()
                raise
            return driver

        driver = await connect_with_retry(
            component=_COMPONENT_NAME,
            attempt=_attempt,
            settings=self._infra_settings,
            logger=self._logger,
        )
        if driver is not None:
            self._driver = driver
            self._logger.info("infrastructure.connected", component=_COMPONENT_NAME)

    async def disconnect(self) -> None:
        if self._driver is not None:
            await self._driver.close()
            self._driver = None
            self._logger.info("infrastructure.disconnected", component=_COMPONENT_NAME)

    async def health_check(self) -> ComponentHealth:
        if self._driver is None:
            return ComponentHealth(name=_COMPONENT_NAME, status="unavailable")
        start = perf_counter()
        try:
            await self._driver.verify_connectivity()
        except Exception as exc:
            return ComponentHealth(
                name=_COMPONENT_NAME, status="unavailable", detail=str(exc)
            )
        return ComponentHealth(
            name=_COMPONENT_NAME,
            status="healthy",
            latency_ms=(perf_counter() - start) * 1000,
        )
