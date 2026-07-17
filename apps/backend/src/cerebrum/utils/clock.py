"""A time source abstracted behind a Protocol, so anything that needs
"now" (request timing, health-response timestamps, future audit records)
depends on an injectable interface rather than calling
``datetime.now()`` directly — supporting the Testability principle: a
test can inject a fixed clock instead of monkeypatching the standard
library.
"""

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    """Anything that can report the current instant."""

    def now(self) -> datetime: ...


class SystemClock:
    """The real clock, backed by the system time. The only instance used
    outside of tests.
    """

    def now(self) -> datetime:
        return datetime.now(UTC)


def utcnow() -> datetime:
    """A timezone-aware UTC timestamp. Prefer :class:`Clock` injection in
    testable code paths; this free function exists for the many call
    sites (schema field defaults, module-level constants) where a
    Protocol cannot be injected.
    """
    return datetime.now(UTC)
