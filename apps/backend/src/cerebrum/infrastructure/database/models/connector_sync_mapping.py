"""``ConnectorSyncMapping``: the provenance and Delta Detection record
tying one external item (a GitHub issue, a Confluence page, a Slack
message, ...) to the
:class:`~cerebrum.infrastructure.database.models.document.Document`
this codebase's existing pipeline created from it — CIS Phase 5 Prompt
1's Change Tracking requirement. Neither ``Document`` nor
``DocumentVersion`` carries any external-system reference of its own
(by design — see cerebrum.application.knowledge.document_service's
docstring: a ``Document`` is source-agnostic), so this is the one place
"which external item produced this document, and was it modified since
we last synced it" is answered.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    TimestampMixin,
    UTCDateTime,
    UUIDPrimaryKeyMixin,
)


class MappingSyncStatus(StrEnum):
    SYNCED = "synced"
    FAILED = "failed"


class ConnectorSyncMapping(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "connector_sync_mappings"
    __table_args__ = (
        UniqueConstraint(
            "connector_id", "external_id", name="uq_connector_sync_mapping_external_id"
        ),
    )

    connector_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connectors.id", ondelete="CASCADE"), index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    external_id: Mapped[str] = mapped_column(String(500), index=True)
    """The source system's own identifier for the item (e.g. a GitHub
    issue's ``"owner/repo#123"``, a Confluence page id) — stable across
    re-syncs, unlike title/content, which is exactly why it is the join
    key rather than a name-based lookup.
    """
    external_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    external_updated_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime, nullable=True
    )
    content_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    """SHA256 of the last-synced normalized content — Delta Detection's
    actual comparison key (an external system's own "updated at"
    timestamp can lag or be absent; comparing content hashes is the
    only mechanism no source can misreport).
    """
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    """Nullable: set once the first sync of this external item
    completes successfully — a mapping row is created *before* the
    document pipeline runs (so a crash mid-sync still leaves a
    Change-Tracking record, per Retry/Resume Failed Sync), then
    populated after
    cerebrum.application.knowledge.upload_service.UploadService and
    cerebrum.application.knowledge.knowledge_preparation_service.KnowledgePreparationService
    both succeed.
    """
    last_synced_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    sync_status: Mapped[str] = mapped_column(
        String(20), default=MappingSyncStatus.SYNCED.value
    )
