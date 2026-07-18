"""Reusable column mixins every model in this package composes, so the
primary-key and timestamp conventions are declared once — per CIS Phase
1 Prompt 4's "no duplicated code" quality standard, carried forward into
Prompt 5's models and extended by CIS Phase 2 Prompt 1's business
entities (Folder, Document, Tag, Label, Collection, ...), which need
soft delete, audit fields, and optimistic locking that the Identity &
Security platform's own tables never needed.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

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


class SoftDeleteMixin:
    """``is_deleted``/``deleted_at`` — satisfies
    :class:`~cerebrum.repositories.soft_delete.SoftDeletable` structurally
    (that Protocol requires no inheritance, but every concrete business
    entity composes this mixin rather than redeclaring the same two
    columns). A soft-deleted row is never returned by a repository's
    default ``list()``/``get_by_id()`` — see
    cerebrum.repositories.postgres.query_utils's filtering convention —
    until :meth:`~cerebrum.repositories.soft_delete.SoftDeleteRepository.restore`
    clears it.
    """

    is_deleted: Mapped[bool] = mapped_column(default=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class AuditFieldsMixin:
    """``created_by``/``updated_by`` — who, not just when (``TimestampMixin``
    already covers when). Nullable: a system-initiated change (e.g. a
    future background job) has no acting user.
    """

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class OptimisticLockMixin:
    """A version counter for optimistic concurrency control — SQLAlchemy's
    native ``version_id_col`` mechanism increments this column on every
    ``UPDATE`` and raises :class:`sqlalchemy.orm.exc.StaleDataError` when
    the ``WHERE version = <the value this session loaded>`` clause
    matches zero rows — i.e., another transaction already changed the
    row since this session read it.

    ``__mapper_args__`` is declared here, on the mixin, as a
    ``@declared_attr`` — not on each concrete model — so composing this
    mixin is sufficient by itself; SQLAlchemy evaluates a mixin's
    ``@declared_attr`` once per concrete mapped class, with ``cls``
    bound to that class, which is what lets ``cls.version`` resolve to
    the concrete model's own mapped column.
    """

    version: Mapped[int] = mapped_column(default=1, nullable=False)

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:
        return {"version_id_col": cls.version}
