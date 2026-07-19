"""``Workflow``: the central entity of CIS Phase 5 Prompt 2's Enterprise
Automation & Workflow Engine. Holds identity, placement (workspace/
tenant), lifecycle status, and a pointer to its current definition —
mirrors cerebrum.infrastructure.database.models.document.Document's
identity/current-version split exactly:
:class:`~cerebrum.infrastructure.database.models.workflow_version.WorkflowVersion`
holds the actual trigger/steps, never this table.
"""

import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    AuditFieldsMixin,
    OptimisticLockMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class WorkflowStatus(StrEnum):
    """Draft -> Active -> Paused -> Archived. ``PAUSED`` blocks *every*
    new run (manual, scheduled, or event-triggered) — see
    cerebrum.application.workflows.workflow_run_service.WorkflowRunService.execute
    — the single mechanism behind the API's "Pause workflow"/"Resume
    workflow" endpoints; there is deliberately no separate per-schedule
    pause state (see
    cerebrum.infrastructure.database.models.workflow_schedule's
    docstring).
    """

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class Workflow(
    Base,
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    SoftDeleteMixin,
    AuditFieldsMixin,
    OptimisticLockMixin,
):
    """``current_version_id`` is nullable only until
    :class:`~cerebrum.application.workflows.workflow_service.WorkflowService.create`
    creates version 1 in the same operation — every ``Workflow`` a
    caller can observe has exactly one current version.
    ``is_template`` flags a workflow as a reusable starting point (CIS
    Phase 5 Prompt 2's Workflow Templates) rather than a live,
    executable automation — see
    :meth:`~cerebrum.application.workflows.workflow_service.WorkflowService.create_from_template`.
    """

    __tablename__ = "workflows"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=WorkflowStatus.DRAFT.value, index=True
    )
    is_template: Mapped[bool] = mapped_column(default=False, index=True)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "workflow_versions.id",
            ondelete="SET NULL",
            # workflow_versions.workflow_id references workflows.id right
            # back — the same genuine circular FK pair
            # cerebrum.infrastructure.database.models.document.Document
            # documents on its current_version_id; use_alter + a name
            # defers this constraint to an ALTER TABLE emitted after
            # both tables exist.
            use_alter=True,
            name="fk_workflows_current_version_id",
        ),
        nullable=True,
    )
    workflow_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
