"""``PostgresClientManager``: the connection-lifecycle owner for the
authoritative relational datastore.

Composes :func:`~cerebrum.infrastructure.database.engine.create_engine`
and :func:`~cerebrum.infrastructure.database.session.create_session_factory`
behind the same connect/disconnect/health_check shape every other
infrastructure client manager implements — see
cerebrum.infrastructure.health.InfrastructureClientManager.
"""

from time import perf_counter

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from structlog.typing import FilteringBoundLogger

from cerebrum.config.database import PostgresSettings
from cerebrum.config.infrastructure import InfrastructureSettings
from cerebrum.infrastructure.database.engine import create_engine
from cerebrum.infrastructure.database.session import create_session_factory
from cerebrum.infrastructure.database.unit_of_work import UnitOfWork
from cerebrum.infrastructure.health import ComponentHealth
from cerebrum.infrastructure.retry import connect_with_retry
from cerebrum.shared.errors.exceptions import InfrastructureException

_COMPONENT_NAME = "postgresql"


class PostgresClientManager:
    """Owns the async engine and session factory for PostgreSQL."""

    def __init__(
        self,
        settings: PostgresSettings,
        infra_settings: InfrastructureSettings,
        logger: FilteringBoundLogger,
    ) -> None:
        self._settings = settings
        self._infra_settings = infra_settings
        self._logger = logger
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def is_connected(self) -> bool:
        return self._engine is not None

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            raise InfrastructureException(
                f"{_COMPONENT_NAME} is not connected — cannot obtain a session factory."
            )
        return self._session_factory

    def create_unit_of_work(self) -> UnitOfWork:
        return UnitOfWork(self.session_factory)

    async def connect(self) -> None:
        async def _attempt() -> AsyncEngine:
            engine = create_engine(
                self._settings.dsn,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
                pool_recycle=1800,
                connect_args={"timeout": self._infra_settings.connect_timeout_seconds},
            )
            try:
                async with engine.connect() as connection:
                    await connection.execute(text("SELECT 1"))
            except Exception:
                # The pool was created even though the verification query
                # failed — dispose it, or a failed attempt leaks pooled
                # connections across each of connect_with_retry's retries.
                await engine.dispose()
                raise
            return engine

        engine = await connect_with_retry(
            component=_COMPONENT_NAME,
            attempt=_attempt,
            settings=self._infra_settings,
            logger=self._logger,
        )
        if engine is not None:
            self._engine = engine
            self._session_factory = create_session_factory(engine)
            self._logger.info("infrastructure.connected", component=_COMPONENT_NAME)

    async def disconnect(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            self._logger.info("infrastructure.disconnected", component=_COMPONENT_NAME)

    async def health_check(self) -> ComponentHealth:
        if self._engine is None:
            return ComponentHealth(name=_COMPONENT_NAME, status="unavailable")
        start = perf_counter()
        try:
            async with self._engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except Exception as exc:
            return ComponentHealth(
                name=_COMPONENT_NAME, status="unavailable", detail=str(exc)
            )
        return ComponentHealth(
            name=_COMPONENT_NAME,
            status="healthy",
            latency_ms=(perf_counter() - start) * 1000,
        )
