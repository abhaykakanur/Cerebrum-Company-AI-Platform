"""Proves the acceptance criterion "Transactions work" from CIS Phase 1
Prompt 4.

Exercises :class:`~cerebrum.infrastructure.database.unit_of_work.UnitOfWork`
against an in-memory SQLite database (via ``aiosqlite``, a dev-only
dependency — see apps/backend/pyproject.toml) rather than PostgreSQL:
the engine/session/UnitOfWork mechanics are dialect-agnostic (see
cerebrum.infrastructure.database.engine's docstring), so this proves the
platform's transaction semantics without requiring a real PostgreSQL
instance in a unit-test environment. A throwaway table defined in this
test module (not under ``cerebrum.infrastructure.database.base.Base``)
is the only way to observe commit/rollback; it is not a step toward an
ORM model in the shipped application — see CIS Phase 1 Prompt 4's "No
ORM models" scope, which governs ``src/cerebrum``, not test fixtures.
"""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from cerebrum.infrastructure.database.engine import create_engine
from cerebrum.infrastructure.database.unit_of_work import UnitOfWork
from cerebrum.shared.errors.exceptions import InfrastructureException

pytestmark = pytest.mark.unit

SessionFactory = async_sessionmaker[AsyncSession]


class _TestBase(DeclarativeBase):
    pass


class _Widget(_TestBase):
    __tablename__ = "widgets"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    test_engine = create_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with test_engine.begin() as connection:
        await connection.run_sync(_TestBase.metadata.create_all)
    yield test_engine
    await test_engine.dispose()


@pytest.fixture
def session_factory(engine: AsyncEngine) -> SessionFactory:
    return async_sessionmaker(bind=engine, expire_on_commit=False)


async def test_commit_persists_changes(session_factory: SessionFactory) -> None:
    uow = UnitOfWork(session_factory)
    async with uow:
        uow.session.add(_Widget(name="alpha"))

    async with session_factory() as verify_session:
        result = await verify_session.execute(select(_Widget))
        assert [w.name for w in result.scalars()] == ["alpha"]


async def test_exception_inside_block_rolls_back(
    session_factory: SessionFactory,
) -> None:
    with pytest.raises(ValueError):
        async with UnitOfWork(session_factory) as uow:
            uow.session.add(_Widget(name="should-not-persist"))
            raise ValueError("simulated failure")

    async with session_factory() as verify_session:
        result = await verify_session.execute(select(_Widget))
        assert list(result.scalars()) == []


async def test_explicit_rollback(session_factory: SessionFactory) -> None:
    uow = UnitOfWork(session_factory)
    await uow.begin()
    uow.session.add(_Widget(name="explicit"))
    await uow.rollback()
    await uow.dispose()

    async with session_factory() as verify_session:
        result = await verify_session.execute(select(_Widget))
        assert list(result.scalars()) == []


async def test_session_property_raises_before_begin(
    session_factory: SessionFactory,
) -> None:
    uow = UnitOfWork(session_factory)
    with pytest.raises(InfrastructureException):
        _ = uow.session


async def test_dispose_is_idempotent(session_factory: SessionFactory) -> None:
    uow = UnitOfWork(session_factory)
    await uow.dispose()  # never begun — must not raise
    await uow.begin()
    await uow.dispose()
    await uow.dispose()  # already disposed — must not raise
