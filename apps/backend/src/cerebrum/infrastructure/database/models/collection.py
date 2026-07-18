"""``Collection`` and its many-to-many membership with
:class:`~cerebrum.infrastructure.database.models.document.Document` —
CIS Phase 2 Prompt 1's Collections (a user-curated grouping, distinct
from :class:`~cerebrum.infrastructure.database.models.folder.Folder`'s
single-parent hierarchy: a document may belong to any number of
Collections simultaneously, but at most one Folder).
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    AuditFieldsMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UTCDateTime,
    UUIDPrimaryKeyMixin,
)
from cerebrum.utils.clock import utcnow


class Collection(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditFieldsMixin
):
    __tablename__ = "collections"
    __table_args__ = (UniqueConstraint("workspace_id", "name"),)

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class CollectionDocument(Base):
    """Membership carries its own ``added_at`` (unlike
    :class:`~cerebrum.infrastructure.database.models.tag.DocumentTag`,
    a pure association) since "when was this document added to this
    collection" is meaningful, orderable information a collection view
    wants to sort/display by.
    """

    __tablename__ = "collection_documents"

    collection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    added_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
