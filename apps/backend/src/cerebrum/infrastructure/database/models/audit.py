"""``AuditEvent``: an append-only security audit trail entry. Audit
events only — no analytics (CIS Phase 1 Prompt 5's scope; see
cerebrum.application.auth.audit_service, not an analytics aggregation).

Does not compose
:class:`~cerebrum.infrastructure.database.models.mixins.TimestampMixin`:
an audit record is immutable once written — an ``updated_at`` column
would imply it can change, which it must not (append-only, per
docs/architecture/specification/38_Observability.md: "a distinct,
append-only, non-deletable stream").
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    UTCDateTime,
    UUIDPrimaryKeyMixin,
)
from cerebrum.utils.clock import utcnow


class AuditEventType(StrEnum):
    """The seven Authentication/Authorization event types CIS Phase 1
    Prompt 5 names explicitly, plus the six Upload/Delete/Restore/
    Download/Validation-failure/Storage-failure events CIS Phase 2
    Prompt 2's Auditing requirement names for the Document domain. Every
    category beyond these is added alongside the feature work that
    produces it.
    """

    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    TOKEN_REFRESH = "token_refresh"
    PERMISSION_DENIED = "permission_denied"
    API_KEY_USED = "api_key_used"
    SESSION_REVOKED = "session_revoked"

    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_UPLOAD_VALIDATION_FAILED = "document_upload_validation_failed"
    DOCUMENT_STORAGE_FAILURE = "document_storage_failure"
    DOCUMENT_DELETED = "document_deleted"
    DOCUMENT_RESTORED = "document_restored"
    DOCUMENT_DOWNLOADED = "document_downloaded"

    CONNECTOR_REGISTERED = "connector_registered"
    CONNECTOR_CONFIGURED = "connector_configured"
    CONNECTOR_DELETED = "connector_deleted"
    CONNECTOR_CREDENTIALS_ACCESSED = "connector_credentials_accessed"
    CONNECTOR_SYNC_STARTED = "connector_sync_started"
    CONNECTOR_SYNC_COMPLETED = "connector_sync_completed"
    CONNECTOR_SYNC_FAILED = "connector_sync_failed"

    WORKFLOW_CREATED = "workflow_created"
    WORKFLOW_UPDATED = "workflow_updated"
    WORKFLOW_DELETED = "workflow_deleted"
    WORKFLOW_STATUS_CHANGED = "workflow_status_changed"
    WORKFLOW_RUN_STARTED = "workflow_run_started"
    WORKFLOW_RUN_COMPLETED = "workflow_run_completed"
    WORKFLOW_RUN_FAILED = "workflow_run_failed"
    WORKFLOW_RUN_CANCELLED = "workflow_run_cancelled"
    WORKFLOW_SCHEDULE_CREATED = "workflow_schedule_created"
    WORKFLOW_SCHEDULE_DELETED = "workflow_schedule_deleted"

    CAPSULE_CREATED = "capsule_created"
    CAPSULE_LINKED = "capsule_linked"
    CAPSULE_REFRESHED = "capsule_refreshed"
    CAPSULE_DELETED = "capsule_deleted"
    CAPSULE_ACCESSED = "capsule_accessed"


class AuditEvent(Base, UUIDPrimaryKeyMixin):
    """``user_id``/``organization_id``/``workspace_id`` are all nullable
    — a ``LOGIN_FAILED`` event, for instance, may have no resolvable
    ``user_id`` if the attempted email doesn't exist (recorded anyway,
    without leaking whether the account exists — see
    docs/architecture/security/security-architecture.md).
    """

    __tablename__ = "audit_events"

    event_type: Mapped[str] = mapped_column(String(50), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, index=True
    )
