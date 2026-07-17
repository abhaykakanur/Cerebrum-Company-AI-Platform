"""Alembic's migration environment.

Reuses the platform's own configuration (``cerebrum.config.settings``)
for the database URL, and the platform's own declarative ``Base`` (see
cerebrum.infrastructure.database.base) as the autogenerate target — a
migration environment with its own, separately-maintained connection
string or model registry would drift from the application's, per CIS
Phase 1 Prompt 4's "no duplicated configuration" quality standard.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from cerebrum.config.settings import get_settings
from cerebrum.infrastructure.database.base import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# No ORM model exists at this milestone (see CIS Phase 1 Prompt 4's "Do
# not create business tables" scope) — Base.metadata is empty, so the
# first `alembic revision --autogenerate` run produces a no-op migration
# until a future phase defines models under Base. The wiring is what
# this milestone establishes, not migration content.
target_metadata = Base.metadata

# The database URL comes from Settings (ultimately POSTGRES_* env vars),
# not from alembic.ini's [alembic] sqlalchemy.url — see this module's
# docstring.
config.set_main_option("sqlalchemy.url", get_settings().postgres.dsn)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
