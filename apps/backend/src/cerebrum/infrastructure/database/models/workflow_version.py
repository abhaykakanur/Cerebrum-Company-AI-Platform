"""``WorkflowVersion``: one immutable, numbered revision of a
:class:`~cerebrum.infrastructure.database.models.workflow.Workflow`'s
trigger and steps — CIS Phase 5 Prompt 2's Workflow Versioning
requirement, mirroring
cerebrum.infrastructure.database.models.document_version.DocumentVersion
exactly: identity fields are immutable once created, only reachable
through
cerebrum.application.workflows.workflow_service.WorkflowService, never
a concurrent multi-writer path optimistic locking would need to guard.
"""

import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class TriggerType(StrEnum):
    """CIS Phase 5 Prompt 2's Trigger types. ``MANUAL`` and
    ``API_REQUEST`` share one execution path (both are simply a caller
    hitting ``POST /workflows/{id}/execute``) — the distinction is
    recorded on the *run*
    (:class:`~cerebrum.infrastructure.database.models.workflow_run.WorkflowRun.trigger_type`),
    not enforced structurally. ``SCHEDULED`` is the only trigger type
    with a live, self-driven firing mechanism (see
    cerebrum.application.workflows.scheduler.WorkflowScheduler);
    ``CONNECTOR_SYNC_COMPLETED``/``DOCUMENT_UPLOADED``/
    ``KNOWLEDGE_UPDATED``/``CUSTOM_EVENT`` are dispatched through
    cerebrum.application.workflows.workflow_run_service.WorkflowRunService.dispatch_event
    — a callable/API-invokable "process this event" method, not a live
    subscription — because
    cerebrum.events.dispatcher.EventDispatcher's handlers are
    synchronous, and firing a workflow run requires awaiting real
    database/service I/O. See that method's docstring for the full
    reasoning.
    """

    MANUAL = "manual"
    SCHEDULED = "scheduled"
    CONNECTOR_SYNC_COMPLETED = "connector_sync_completed"
    DOCUMENT_UPLOADED = "document_uploaded"
    KNOWLEDGE_UPDATED = "knowledge_updated"
    API_REQUEST = "api_request"
    CUSTOM_EVENT = "custom_event"


class StepType(StrEnum):
    """CIS Phase 5 Prompt 2's reusable Workflow Step abstractions. The
    first five call directly into an existing application service (see
    cerebrum.application.workflows.step_executors) — "reuse all existing
    services... do not duplicate connector, retrieval, reasoning or AI
    logic". ``CONDITION``/``DELAY``/``PARALLEL`` are control flow,
    handled by
    cerebrum.application.workflows.workflow_run_service.WorkflowRunService
    itself rather than a step executor, since they recurse back into
    step execution. ``CUSTOM`` is an extension point (see
    cerebrum.application.workflows.step_executors.CustomStepExecutor) —
    no custom handlers ship at this milestone.
    """

    CONNECTOR_ACTION = "connector_action"
    AI_REASONING = "ai_reasoning"
    RETRIEVAL = "retrieval"
    SEARCH = "search"
    NOTIFICATION = "notification"
    CUSTOM = "custom"
    CONDITION = "condition"
    DELAY = "delay"
    PARALLEL = "parallel"


class WorkflowVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "workflow_versions"
    __table_args__ = (UniqueConstraint("workflow_id", "version_number"),)

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), index=True
    )
    version_number: Mapped[int] = mapped_column(Integer)
    trigger_type: Mapped[str] = mapped_column(
        String(30), default=TriggerType.MANUAL.value
    )
    trigger_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
