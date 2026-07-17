"""Shared pytest fixtures for the backend test suite.

See CIS Phase 1 Prompt 3's Testing Foundation requirement: pytest
configuration, fixtures, and test utilities, with no feature tests. The
fixtures below exercise the platform itself (application starts, health
endpoints respond) — proving the acceptance criteria in the prompt, not
testing any business feature.
"""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cerebrum.config.settings import Settings, get_settings


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
    """
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("INFRA_CONNECT_RETRIES", "0")
    monkeypatch.setenv("INFRA_CONNECT_TIMEOUT_SECONDS", "0.3")
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
