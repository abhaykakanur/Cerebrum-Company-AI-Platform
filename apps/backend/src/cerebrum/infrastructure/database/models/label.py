"""``Label`` and its many-to-many association with
:class:`~cerebrum.infrastructure.database.models.document.Document` —
CIS Phase 2 Prompt 1's structured Labels. A Label carries a ``color``
and is intended for a smaller, curated classification taxonomy (e.g.
"Confidential", "Public"), distinct from
:class:`~cerebrum.infrastructure.database.models.tag.Tag`'s free-form,
uncolored, many-per-document text — both are still many-to-many with
Document; the distinction is intended usage, not cardinality.
"""

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Label(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "labels"
    __table_args__ = (UniqueConstraint("workspace_id", "name"),)

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    """A ``#rrggbb`` hex string, or ``NULL`` for no assigned color —
    validated at the API/service layer, not this column, per this
    codebase's "structural validation is a Pydantic/service concern"
    convention.
    """


class DocumentLabel(Base):
    __tablename__ = "document_labels"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    label_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True
    )
