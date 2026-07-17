"""The shared connection-retry helper every client manager's ``connect()``
uses, so retry/backoff behavior is implemented exactly once — per CIS
Phase 1 Prompt 4's "no duplicated code" quality standard — rather than
six near-identical retry loops.
"""

import asyncio
from collections.abc import Awaitable, Callable

from structlog.typing import FilteringBoundLogger

from cerebrum.config.infrastructure import InfrastructureSettings


async def connect_with_retry[T](
    *,
    component: str,
    attempt: Callable[[], Awaitable[T]],
    settings: InfrastructureSettings,
    logger: FilteringBoundLogger,
) -> T | None:
    """Calls ``attempt()`` up to ``1 + settings.connect_retries`` times,
    with exponential backoff between attempts starting at
    ``settings.connect_retry_backoff_seconds``.

    Returns the attempt's result on success, or ``None`` once every
    attempt has failed — the caller (a client manager's ``connect()``)
    is expected to treat ``None`` as "leave this client disconnected,"
    never to propagate the underlying driver exception. Every attempt's
    failure and the final give-up are logged, so the cause is always
    visible in structured logs even though it never reaches an API
    response.
    """
    last_error: Exception | None = None
    total_attempts = 1 + settings.connect_retries

    for attempt_number in range(1, total_attempts + 1):
        try:
            return await attempt()
        except Exception as exc:  # intentionally broad — see module docstring.
            last_error = exc
            if attempt_number < total_attempts:
                backoff = settings.connect_retry_backoff_seconds * (
                    2 ** (attempt_number - 1)
                )
                logger.warning(
                    "infrastructure.connect_retry",
                    component=component,
                    attempt=attempt_number,
                    total_attempts=total_attempts,
                    backoff_seconds=backoff,
                    error=str(exc),
                )
                await asyncio.sleep(backoff)

    logger.error(
        "infrastructure.connect_failed",
        component=component,
        total_attempts=total_attempts,
        error=str(last_error),
    )
    return None
