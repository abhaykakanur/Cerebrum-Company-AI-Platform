"""``DocumentVersion``: one immutable, numbered revision of a
:class:`~cerebrum.infrastructure.database.models.document.Document`'s
content — CIS Phase 2 Prompt 1's Versioning requirement. The binary
content itself never lives here or in PostgreSQL at all — see
cerebrum.infrastructure.database.models.document_metadata.
"""

import uuid
from enum import StrEnum

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class VersionType(StrEnum):
    """CIS Phase 2 Prompt 1's Major/Minor distinction — a caller-supplied
    classification (this table does not itself enforce semantic version
    numbering rules beyond ``version_number`` being a strictly
    incrementing integer per document — see
    cerebrum.application.knowledge.version_service).
    """

    MAJOR = "major"
    MINOR = "minor"


class UploadStatus(StrEnum):
    """CIS Phase 2 Prompt 2's upload-pipeline lifecycle for one version's
    underlying file, distinct from
    :class:`~cerebrum.infrastructure.database.models.document.DocumentStatus`
    (the owning Document's own, coarser lifecycle):
    Uploaded -> Validated -> Stored -> Ready For Processing -> Archived
    -> Deleted, plus ``QUARANTINED`` (see
    cerebrum.infrastructure.security.virus_scan) as a terminal failure
    state a validated-but-flagged upload lands in instead of ``STORED``.
    """

    UPLOADED = "uploaded"
    VALIDATED = "validated"
    STORED = "stored"
    READY_FOR_PROCESSING = "ready_for_processing"
    ARCHIVED = "archived"
    DELETED = "deleted"
    QUARANTINED = "quarantined"


class DocumentVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """No soft delete, no optimistic lock: a version's identity fields
    (``document_id``, ``version_number``) are immutable once created —
    only ``is_current``/``upload_status``/``change_summary`` ever change,
    and always through
    cerebrum.application.knowledge.version_service, never a concurrent
    multi-writer path optimistic locking would need to guard.
    """

    __tablename__ = "document_versions"
    __table_args__ = (UniqueConstraint("document_id", "version_number"),)

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    version_number: Mapped[int] = mapped_column(Integer)
    version_type: Mapped[str] = mapped_column(
        String(10), default=VersionType.MINOR.value
    )
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    upload_status: Mapped[str] = mapped_column(
        String(30), default=UploadStatus.UPLOADED.value, index=True
    )
    change_summary: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
