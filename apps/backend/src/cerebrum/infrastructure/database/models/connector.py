"""``Connector``: a configured integration with an external enterprise
system — CIS Phase 5 Prompt 1's Connector Framework. Holds
configuration, health, and scheduling state only; the actual
sync-history/progress bookkeeping lives in
:class:`~cerebrum.infrastructure.database.models.connector_sync_run.ConnectorSyncRun`,
and per-item provenance/delta-detection state lives in
:class:`~cerebrum.infrastructure.database.models.connector_sync_mapping.ConnectorSyncMapping`
— the same "one row of identity/lifecycle, separate rows for the
activity it produces" split
cerebrum.infrastructure.database.models.document.Document's docstring
established for ``Document``/``DocumentVersion``.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    AuditFieldsMixin,
    OptimisticLockMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UTCDateTime,
    UUIDPrimaryKeyMixin,
)


class ConnectorType(StrEnum):
    """CIS Phase 5 Prompt 1's nine named Knowledge Sources, grouped by
    category in the spec (Development/Project Management/Documentation/
    Communication) — flattened here into one enum since nothing in this
    codebase queries by category, only by concrete type.
    """

    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    JIRA = "jira"
    AZURE_DEVOPS = "azure_devops"
    CONFLUENCE = "confluence"
    NOTION = "notion"
    SLACK = "slack"
    TEAMS = "teams"


class ConnectorAuthType(StrEnum):
    """CIS Phase 5 Prompt 1's four provider-independent authentication
    methods — see cerebrum.infrastructure.connectors.auth for how each
    is turned into real request headers/params.
    """

    OAUTH2 = "oauth2"
    PERSONAL_ACCESS_TOKEN = "personal_access_token"
    API_KEY = "api_key"
    SERVICE_ACCOUNT = "service_account"


class ConnectorStatus(StrEnum):
    """CIS Phase 5 Prompt 1's Connector Lifecycle: Active -> Paused ->
    Error -> Disabled. ``ERROR`` is set automatically by
    cerebrum.application.connectors.connector_sync_service.ConnectorSyncService
    when a sync run fails; ``PAUSED``/``DISABLED`` are caller-driven
    (paused: temporarily excluded from scheduled sync; disabled: the
    soft-delete-adjacent "never sync again" terminal state, mirroring
    cerebrum.infrastructure.database.models.document.DocumentStatus's
    ``DELETED`` convention of a status flag alongside, not instead of,
    :class:`~cerebrum.infrastructure.database.models.mixins.SoftDeleteMixin`).
    """

    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    DISABLED = "disabled"


class ConnectorHealthStatus(StrEnum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


class Connector(
    Base,
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    SoftDeleteMixin,
    AuditFieldsMixin,
    OptimisticLockMixin,
):
    __tablename__ = "connectors"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    connector_type: Mapped[str] = mapped_column(String(30), index=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        String(20), default=ConnectorStatus.ACTIVE.value, index=True
    )
    auth_type: Mapped[str] = mapped_column(String(30))
    credentials: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    """Connector Configuration's secret half — OAuth2 tokens/PATs/API
    keys/service-account keys. **Never** serialized into an API
    response (see cerebrum.api.schemas.connector's docstring for
    "Secret Isolation") — the existing configuration framework's
    ``SecretStr`` discipline
    (cerebrum.config.ai.AISettings/cerebrum.config.security.SecuritySettings)
    governs deployment-wide provider keys read once from the
    environment; a connector's credentials are per-connector-instance
    and caller-supplied at registration time, so they are wrapped in
    ``SecretStr`` only when loaded into a runtime
    :class:`~cerebrum.infrastructure.connectors.base.ConnectorCredentials`
    object (see that module), never held as a bare string in application
    code. Encryption-at-rest for this column is Deferred to
    Architecture — the same "local-development placeholder, real
    secrets backend is a future Security Domain concern" honesty
    cerebrum.config.settings's ``_DEFAULT_SECRET_PLACEHOLDER`` docstring
    already established for deployment-wide secrets.
    """
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    """Connector Configuration's non-secret half — e.g. a repository
    owner/name, a Confluence space key, a Slack channel id, a base URL
    for a self-hosted instance. Freely returned in API responses.
    """
    health_status: Mapped[str] = mapped_column(
        String(20), default=ConnectorHealthStatus.UNKNOWN.value
    )
    health_checked_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime, nullable=True
    )
    health_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    sync_interval_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """``None`` — Manual Sync only. A positive value opts into
    Scheduled/Periodic Sync — see
    cerebrum.application.connectors.scheduler's docstring for why this
    codebase computes *when* a connector is due rather than itself
    executing on a timer (no background worker runtime exists yet —
    see cerebrum.config.worker.WorkerSettings).
    """
    last_sync_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime, nullable=True
    )
    next_sync_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
