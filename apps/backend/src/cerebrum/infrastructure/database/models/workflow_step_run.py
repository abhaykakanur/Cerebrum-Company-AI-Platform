"""``WorkflowStepRun``: one step's execution record within a single
:class:`~cerebrum.infrastructure.database.models.workflow_run.WorkflowRun`
— CIS Phase 5 Prompt 2's Step Duration/Success Rate/Failure
Reason/Execution Logs observability. Persisted per step (not only at
run completion) so a concurrent reader of the same transaction sees
real-time progress — see
cerebrum.application.workflows.workflow_run_service's module docstring
for why sub-step granularity beyond this is not meaningful in a
worker-less, single-request execution model.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    UTCDateTime,
    UUIDPrimaryKeyMixin,
)


class WorkflowStepRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class WorkflowStepRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "workflow_step_runs"

    workflow_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"), index=True
    )
    step_id: Mapped[str] = mapped_column(String(100))
    step_type: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(
        String(20), default=WorkflowStepRunStatus.PENDING.value, index=True
    )
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
