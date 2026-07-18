"""Reusable column mixins every model in this package composes, so the
primary-key and timestamp conventions are declared once — per CIS Phase
1 Prompt 4's "no duplicated code" quality standard, carried forward into
Prompt 5's models.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.utils.clock import utcnow

# Every datetime column in this package uses DateTime(timezone=True)
# explicitly. Without it, SQLAlchemy stores (and reads back) a naive
# datetime on both PostgreSQL and SQLite even though the Python-side
# default below always produces a UTC-aware one — comparing that naive
# value against a fresh `utcnow()` call (e.g. UserSession.is_active)
# would raise TypeError. This module-level constant is the one place
# that column type is spelled out, so every model uses it identically.
UTCDateTime = DateTime(timezone=True)


class UUIDPrimaryKeyMixin:
    """A UUIDv4 primary key, generated in Python (not server-side) —
    portable across every dialect this codebase targets (PostgreSQL in
    production, SQLite in tests — see
    apps/backend/tests/unit/test_unit_of_work.py), and reuses
    :func:`cerebrum.utils.clock.utcnow`'s pattern of Python-side
    generation over a server function.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    """``created_at``/``updated_at``, both Python-side via
    :func:`cerebrum.utils.clock.utcnow` — reusing the same clock every
    other timestamp in this codebase (``RequestContext``, health
    responses, domain events) already uses, rather than a
    dialect-specific server default.
    """

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, onupdate=utcnow
    )
