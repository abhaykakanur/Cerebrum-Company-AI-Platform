"""``ConnectorSyncRun``: one execution of a
:class:`~cerebrum.infrastructure.database.models.connector.Connector`'s
sync — CIS Phase 5 Prompt 1's Observability requirement (sync history,
duration, items processed, failures, last successful sync). Append-only
in spirit (a run's terminal fields are only ever set once, by
cerebrum.application.connectors.connector_sync_service.ConnectorSyncService),
the same "many rows of activity per one row of owning identity" shape
cerebrum.infrastructure.database.models.message.Message's docstring
established for ``Conversation``/``Message``.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    UTCDateTime,
    UUIDPrimaryKeyMixin,
)


class SyncRunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SyncType(StrEnum):
    """CIS Phase 5 Prompt 1's Synchronization requirement names four
    distinct sync triggers; ``INCREMENTAL`` is what
    :attr:`~cerebrum.infrastructure.database.models.connector.Connector.sync_interval_seconds`-driven
    Scheduled Sync actually runs once ``INITIAL`` has completed once.
    """

    INITIAL = "initial"
    INCREMENTAL = "incremental"
    MANUAL = "manual"
    FULL_RESYNC = "full_resync"


class ConnectorSyncRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "connector_sync_runs"

    connector_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connectors.id", ondelete="CASCADE"), index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    sync_type: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(
        String(20), default=SyncRunStatus.RUNNING.value, index=True
    )
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    items_discovered: Mapped[int] = mapped_column(Integer, default=0)
    items_processed: Mapped[int] = mapped_column(Integer, default=0)
    items_skipped: Mapped[int] = mapped_column(Integer, default=0)
    """Delta Detection's counter — items whose content was unchanged
    since the last sync, so the existing document pipeline was never
    invoked for them (see ``ConnectorSyncService``'s docstring).
    """
    items_failed: Mapped[int] = mapped_column(Integer, default=0)
    cursor: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    """Delta Detection / pagination bookmark — a connector-specific
    opaque token (e.g. a "since" timestamp or an API-provided page
    cursor) letting Resume Failed Sync continue from where a prior run
    left off rather than re-scanning every item.
    """
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    """``None`` for a scheduler-triggered run — Manual Sync's "who"."""
