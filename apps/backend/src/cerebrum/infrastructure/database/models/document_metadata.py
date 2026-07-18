"""``DocumentMetadata``: the one-to-one metadata record for a
:class:`~cerebrum.infrastructure.database.models.document_version.DocumentVersion`'s
underlying binary object — CIS Phase 2 Prompt 1's "Store only metadata
in PostgreSQL. Store binary object references in MinIO." The binary
bytes themselves are never in this table, never in PostgreSQL at all —
``storage_path`` is a MinIO object key, resolved through
cerebrum.infrastructure.storage (CIS Phase 2 Prompt 2 wires the actual
upload/download).
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    UTCDateTime,
    UUIDPrimaryKeyMixin,
)


class QuarantineStatus(StrEnum):
    """CIS Phase 2 Prompt 2's Quarantine status — the outcome of
    cerebrum.infrastructure.security.virus_scan's ``VirusScanner`` port.
    ``PENDING`` until a scan actually runs; every upload starts here.
    """

    PENDING = "pending"
    CLEAN = "clean"
    QUARANTINED = "quarantined"


class DocumentMetadata(Base, UUIDPrimaryKeyMixin):
    """No ``TimestampMixin``: ``uploaded_at`` is this table's one
    meaningful timestamp, and it is set once, at creation, never updated
    — a new upload is a new :class:`DocumentVersion` (and a new
    ``DocumentMetadata`` row), never a mutation of an existing one,
    mirroring :class:`~cerebrum.infrastructure.database.models.audit.AuditEvent`'s
    same reasoning.
    """

    __tablename__ = "document_metadata"

    document_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    mime_type: Mapped[str] = mapped_column(String(255))
    file_size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256_checksum: Mapped[str] = mapped_column(String(64), index=True)
    storage_path: Mapped[str] = mapped_column(String(1024))
    """The MinIO object key — see
    cerebrum.infrastructure.storage.manager.MinIOClientManager and
    cerebrum.config.minio.MinIOSettings.bucket for which bucket it
    resolves against.
    """
    original_filename: Mapped[str] = mapped_column(String(500))
    uploaded_filename: Mapped[str] = mapped_column(String(500))
    """The name actually used in storage — may differ from
    ``original_filename`` (e.g. sanitized/de-duplicated), per CIS Phase
    2 Prompt 1's distinct Original/Uploaded filename fields.
    """
    uploaded_at: Mapped[datetime] = mapped_column(UTCDateTime)
    quarantine_status: Mapped[str] = mapped_column(
        String(20), default=QuarantineStatus.PENDING.value, index=True
    )
