"""The async session factory, and the FastAPI dependency that yields one
scoped session per request.

A SQLAlchemy ``AsyncSession`` is inherently request-scoped (it tracks an
in-progress unit of work) — never a singleton, unlike the engine it is
built from. See ``cerebrum.dependencies.database.DbSessionDep`` for how
route handlers consume this.
"""

from collections.abc import AsyncIterator

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from cerebrum.shared.errors.exceptions import InfrastructureException


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """A session factory bound to ``engine``. ``expire_on_commit=False``
    so an object returned by a use case remains usable (e.g., serialized
    into a response) after the session that loaded it has committed.
    """
    return async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


async def get_db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Yields one session per request, rolling back on any unhandled
    exception and always closing the session on exit. Never leaks the
    underlying driver exception — see CIS Phase 1 Prompt 4's "never leak
    driver exceptions" rule.

    Not itself a FastAPI dependency (it needs a bound ``session_factory``,
    which only exists once
    :class:`~cerebrum.infrastructure.database.manager.PostgresClientManager`
    has connected) — see ``cerebrum.dependencies.database.get_db_session``
    for the request-time wrapper that supplies it from
    :class:`~cerebrum.core.state.ApplicationState`.
    """
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except SQLAlchemyError as exc:
            await session.rollback()
            raise InfrastructureException(
                "Database session failed.", cause=exc
            ) from exc
        except Exception:
            await session.rollback()
            raise
