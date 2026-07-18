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


def ensure_utc(value: datetime) -> datetime:
    """Normalizes a possibly-naive datetime to UTC-aware.

    Every datetime this codebase writes to a database column is already
    UTC-aware (via :func:`utcnow`) — but SQLite's DBAPI driver does not
    reliably round-trip a ``DateTime(timezone=True)`` column's tzinfo the
    way PostgreSQL's does (a documented SQLAlchemy+SQLite limitation: it
    stores an ISO string and parses it back without timezone
    reconstruction). A value read back naive is assumed UTC — the only
    timezone this codebase ever writes — rather than treated as
    ambiguous. See e.g.
    :attr:`~cerebrum.infrastructure.database.models.session.UserSession.is_active`,
    which compares a stored ``expires_at`` against a fresh ``utcnow()``
    and would otherwise raise ``TypeError`` comparing naive to aware.
    """
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
