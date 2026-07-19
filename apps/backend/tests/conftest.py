"""Shared pytest fixtures for the backend test suite.

See CIS Phase 1 Prompt 3's Testing Foundation requirement: pytest
configuration, fixtures, and test utilities, with no feature tests. The
fixtures below exercise the platform itself (application starts, health
endpoints respond) — proving the acceptance criteria in the prompt, not
testing any business feature. ``db_session``/``db_client`` (CIS Phase 1
Prompt 5) extend this with an in-memory SQLite-backed database for tests
that need real persistence — see
apps/backend/tests/unit/test_unit_of_work.py's docstring for why SQLite
is an acceptable stand-in for PostgreSQL in this specific role.
"""

from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from cerebrum.config.settings import Settings, get_settings
from cerebrum.dependencies.database import get_db_session

# Imported for its side effect: populating Base.metadata with every
# model, so create_all below creates every table — see
# cerebrum.infrastructure.database.models's package docstring.
from cerebrum.infrastructure.database import models as _models  # noqa: F401
from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.engine import create_engine


def _settings_classes() -> list[type[BaseSettings]]:
    """``Settings`` itself plus every nested ``BaseSettings`` subclass it's
    composed of (``PostgresSettings``, ``SecuritySettings``, ...) —
    discovered reflectively from ``Settings.model_fields`` so this list
    can't silently drift as new subsystems are added, unlike a
    hand-maintained one.
    """
    classes: list[type[BaseSettings]] = [Settings]
    for field in Settings.model_fields.values():
        annotation = field.annotation
        if isinstance(annotation, type) and issubclass(annotation, BaseSettings):
            classes.append(annotation)
    return classes


@pytest.fixture(autouse=True)
def _isolate_dotenv_from_tests() -> Iterator[None]:
    """No test may depend on what a contributor's real repository-root
    ``.env`` happens to contain. ``cerebrum.config.ENV_FILE`` is
    deliberately resolved independent of the current working directory
    (see that module's docstring — it used to be CWD-relative, which
    silently broke `alembic`/`uvicorn` invocations from `apps/backend/`)
    so the real application reliably finds it — but that same
    reliability means every ``BaseSettings`` subclass would otherwise
    silently pick up a developer's actual local credentials during a
    test run instead of falling through to its intended hardcoded
    default. That's exactly what
    ``test_production_rejects_each_default_secret_placeholder`` (see
    ``test_configuration.py``) asserts about: it deletes an env var and
    expects the *hardcoded* placeholder to still be there, not whatever
    a real `.env` happens to say. Patched once here, for every test,
    since no test should ever be sensitive to ambient `.env` content —
    an explicit ``monkeypatch.setenv(...)`` inside a test still wins
    (environment variables outrank `.env` file values in pydantic-settings'
    precedence), so this doesn't change any test that already sets what
    it needs directly.
    """
    originals = [(cls, cls.model_config.get("env_file")) for cls in _settings_classes()]
    for cls, _ in originals:
        cls.model_config["env_file"] = None
    try:
        yield
    finally:
        for cls, original in originals:
            cls.model_config["env_file"] = original


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[Settings]:
    """A fresh, testing-environment Settings instance, independent of
    :func:`get_settings`'s process-wide cache — see that function's
    docstring.

    Infrastructure connect retries/timeout are pinned low so a test that
    boots the full application (see the ``app``/``client`` fixtures)
    fails fast against the unreachable datastores in a unit-test
    environment, rather than spending real seconds retrying with
    backoff — see cerebrum.config.infrastructure.InfrastructureSettings.
    The login rate limit is raised far above what any test could
    plausibly trigger: this machine's ambient environment may have a
    real, reachable Redis (see
    cerebrum.dependencies.auth.enforce_login_rate_limit's fail-open
    behavior when it doesn't), and a real Redis's counters are not reset
    between test runs — a low limit here would make unrelated tests
    flaky depending on prior runs' leftover state. The dedicated rate
    limit test constructs its own isolated, low-limit
    :class:`~cerebrum.infrastructure.security.rate_limiter.RateLimiter`
    directly instead of going through this fixture.
    """
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("INFRA_CONNECT_RETRIES", "0")
    monkeypatch.setenv("INFRA_CONNECT_TIMEOUT_SECONDS", "0.3")
    monkeypatch.setenv("SECURITY_LOGIN_RATE_LIMIT_ATTEMPTS", "1000000")
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    from cerebrum.core.factory import create_application

    return create_application(settings)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def db_engine() -> AsyncIterator[AsyncEngine]:
    """A fresh in-memory SQLite database, schema created from
    ``Base.metadata`` (every model in
    cerebrum.infrastructure.database.models). ``StaticPool`` keeps the
    one underlying connection alive for the engine's lifetime — an
    in-memory SQLite database otherwise disappears the moment its single
    connection closes, which would happen between every session
    otherwise.
    """
    engine = create_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
def db_session_factory(db_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=db_engine, expire_on_commit=False)


@pytest.fixture
async def db_session(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """A session for tests that call repositories/application services
    directly — the caller controls commit/rollback, matching how a real
    :class:`~cerebrum.infrastructure.database.unit_of_work.UnitOfWork`
    or request-scoped session behaves.
    """
    async with db_session_factory() as session:
        yield session


@pytest.fixture
def db_client(
    app: FastAPI, db_session_factory: async_sessionmaker[AsyncSession]
) -> Iterator[TestClient]:
    """Like :func:`client`, but with
    :func:`~cerebrum.dependencies.database.get_db_session` overridden to
    the SQLite database above instead of the (unreachable, in a unit-test
    environment) real PostgreSQL — for HTTP-level tests of routes that
    touch the database (cerebrum.api.v1.auth). Every other test's
    ``client`` fixture is deliberately left untouched: several existing
    tests (see test_health.py) specifically verify behavior when the
    database is *not* connected.
    """

    async def _override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with db_session_factory() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_db_session] = _override_get_db_session
    with TestClient(app) as test_client:
        yield test_client
    del app.dependency_overrides[get_db_session]
