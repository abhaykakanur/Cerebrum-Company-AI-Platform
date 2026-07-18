"""``Document``: the central entity of CIS Phase 2 Prompt 1's Knowledge
Domain. Holds no binary content itself — see
cerebrum.infrastructure.database.models.document_metadata's docstring
for where the MinIO object reference lives — only identity, placement
(workspace/folder), and lifecycle status.
"""

import uuid
from enum import StrEnum

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    AuditFieldsMixin,
    OptimisticLockMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class DocumentStatus(StrEnum):
    """CIS Phase 2 Prompt 1's Document Lifecycle:
    Draft -> Uploaded -> Active -> Archived -> Deleted. ``DELETED`` is
    set alongside (not instead of)
    :class:`~cerebrum.infrastructure.database.models.mixins.SoftDeleteMixin`'s
    ``is_deleted``/``deleted_at`` when a document is deleted — the flag
    drives repository-level soft-delete filtering, this status documents
    the conceptual lifecycle stage to an API consumer.
    """

    DRAFT = "draft"
    UPLOADED = "uploaded"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class Document(
    Base,
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    SoftDeleteMixin,
    AuditFieldsMixin,
    OptimisticLockMixin,
):
    """``folder_id`` nullable: ``NULL`` places the document at the
    workspace root. ``current_version_id`` is nullable and only set once
    at least one
    :class:`~cerebrum.infrastructure.database.models.document_version.DocumentVersion`
    exists — a ``Draft`` document may have none yet. Deliberately no
    ``ForeignKey`` cycle validation at the database level between
    ``current_version_id`` and ``document_versions.document_id`` (both
    reference each other indirectly); see
    cerebrum.application.knowledge.version_service for the consistency
    check that keeps them aligned.
    """

    __tablename__ = "documents"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    folder_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("folders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        String(20), default=DocumentStatus.DRAFT.value, index=True
    )
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "document_versions.id",
            ondelete="SET NULL",
            # document_versions.document_id references documents.id right
            # back — a genuine circular FK pair. use_alter + a name make
            # SQLAlchemy (both Base.metadata.create_all for tests and the
            # hand-written Alembic migration) emit this one as
            # ALTER TABLE ... ADD CONSTRAINT after both tables exist,
            # rather than failing to order two mutually-dependent
            # CREATE TABLE statements.
            use_alter=True,
            name="fk_documents_current_version_id",
        ),
        nullable=True,
    )
