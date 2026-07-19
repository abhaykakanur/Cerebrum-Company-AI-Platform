"""``WorkflowSchedule``: CIS Phase 5 Prompt 2's Scheduler — Cron
Scheduling and One-Time Execution. Computes/records *when* a
:class:`~cerebrum.infrastructure.database.models.workflow.Workflow`
should next run automatically; whether it is *allowed* to run at all
right now is governed entirely by
:attr:`~cerebrum.infrastructure.database.models.workflow.Workflow.status`
(``PAUSED``/``ARCHIVED`` block every trigger, including a due
schedule) — there is deliberately no independent pause state on the
schedule itself, avoiding two overlapping "is this thing allowed to
run" flags.

Like
:class:`~cerebrum.infrastructure.database.models.connector.Connector`,
this is a long-lived, mutable, operator-facing configuration row (not
an immutable log entry like
:class:`~cerebrum.infrastructure.database.models.workflow_run.WorkflowRun`),
so it composes the same soft-delete/audit-fields mixins.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    AuditFieldsMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UTCDateTime,
    UUIDPrimaryKeyMixin,
)


class ScheduleType(StrEnum):
    CRON = "cron"
    ONE_TIME = "one_time"


class ScheduleStatus(StrEnum):
    """``ACTIVE`` until
    cerebrum.application.workflows.scheduler.WorkflowScheduler.run_due_workflows
    fires it; a ``ONE_TIME`` schedule then becomes ``COMPLETED``
    (terminal — it will never be due again). A ``CRON`` schedule stays
    ``ACTIVE`` forever, its ``next_run_at`` simply advancing.
    """

    ACTIVE = "active"
    COMPLETED = "completed"


class WorkflowSchedule(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditFieldsMixin
):
    __tablename__ = "workflow_schedules"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    schedule_type: Mapped[str] = mapped_column(String(20))
    cron_expression: Mapped[str | None] = mapped_column(String(120), nullable=True)
    run_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=ScheduleStatus.ACTIVE.value, index=True
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime, nullable=True, index=True
    )
    last_run_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
