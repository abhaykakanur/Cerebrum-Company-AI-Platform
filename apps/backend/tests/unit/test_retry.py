"""Proves the acceptance criterion "Retry policies exist" from CIS Phase
1 Prompt 4, using a fake attempt function — no real infrastructure
client is involved, per that prompt's "Mock support" testing
requirement.
"""

import pytest
import structlog

from cerebrum.config.infrastructure import InfrastructureSettings
from cerebrum.infrastructure.retry import connect_with_retry

pytestmark = pytest.mark.unit

_logger = structlog.get_logger()


async def test_succeeds_on_first_attempt() -> None:
    calls = 0

    async def attempt() -> str:
        nonlocal calls
        calls += 1
        return "connected"

    settings = InfrastructureSettings(
        connect_retries=3, connect_retry_backoff_seconds=0.01
    )
    result = await connect_with_retry(
        component="fake", attempt=attempt, settings=settings, logger=_logger
    )
    assert result == "connected"
    assert calls == 1


async def test_succeeds_after_transient_failures() -> None:
    calls = 0

    async def attempt() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ConnectionError("transient")
        return "connected"

    settings = InfrastructureSettings(
        connect_retries=3, connect_retry_backoff_seconds=0.01
    )
    result = await connect_with_retry(
        component="fake", attempt=attempt, settings=settings, logger=_logger
    )
    assert result == "connected"
    assert calls == 3


async def test_gives_up_after_exhausting_retries() -> None:
    calls = 0

    async def attempt() -> str:
        nonlocal calls
        calls += 1
        raise ConnectionError("always fails")

    settings = InfrastructureSettings(
        connect_retries=2, connect_retry_backoff_seconds=0.01
    )
    result = await connect_with_retry(
        component="fake", attempt=attempt, settings=settings, logger=_logger
    )
    assert result is None
    assert calls == 3  # the first attempt plus two retries


async def test_zero_retries_means_exactly_one_attempt() -> None:
    calls = 0

    async def attempt() -> str:
        nonlocal calls
        calls += 1
        raise ConnectionError("fails")

    settings = InfrastructureSettings(
        connect_retries=0, connect_retry_backoff_seconds=0.01
    )
    result = await connect_with_retry(
        component="fake", attempt=attempt, settings=settings, logger=_logger
    )
    assert result is None
    assert calls == 1
