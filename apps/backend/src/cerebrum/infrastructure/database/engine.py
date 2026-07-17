"""The async SQLAlchemy engine factory.

Takes a raw DSN and passes through arbitrary engine keyword arguments,
rather than accepting a :class:`~cerebrum.config.database.PostgresSettings`
directly — pool tuning is dialect-specific (see
:class:`~cerebrum.infrastructure.database.manager.PostgresClientManager`,
which supplies PostgreSQL's pool settings), and this indirection lets
tests point the same factory at an in-memory SQLite database (see
apps/backend/tests/unit/test_unit_of_work.py) with SQLite-appropriate
arguments to exercise transaction behavior without a real PostgreSQL
instance.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def create_engine(dsn: str, *, echo: bool = False, **engine_kwargs: Any) -> AsyncEngine:
    """Builds an async engine. ``engine_kwargs`` is passed through
    verbatim to :func:`sqlalchemy.ext.asyncio.create_async_engine`.
    """
    return create_async_engine(dsn, echo=echo, **engine_kwargs)
