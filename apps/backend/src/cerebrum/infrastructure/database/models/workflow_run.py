"""``WorkflowRun``: one execution of a
:class:`~cerebrum.infrastructure.database.models.workflow.Workflow`'s
current (or a pinned)
:class:`~cerebrum.infrastructure.database.models.workflow_version.WorkflowVersion`
— CIS Phase 5 Prompt 2's Execution History/Observability. No soft
delete, audit fields, or optimistic lock: mutated in place by exactly
one owner,
cerebrum.application.workflows.workflow_run_service.WorkflowRunService,
never a concurrent multi-writer path — the same reasoning
cerebrum.infrastructure.database.models.connector_sync_run.ConnectorSyncRun
documents for its identical mixin choice.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    UTCDateTime,
    UUIDPrimaryKeyMixin,
)


class WorkflowRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "workflow_runs"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), index=True
    )
    workflow_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_versions.id", ondelete="CASCADE")
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default=WorkflowRunStatus.PENDING.value, index=True
    )
    trigger_type: Mapped[str] = mapped_column(String(30))
    trigger_context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    variables: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancellation_requested: Mapped[bool] = mapped_column(Boolean, default=False)
