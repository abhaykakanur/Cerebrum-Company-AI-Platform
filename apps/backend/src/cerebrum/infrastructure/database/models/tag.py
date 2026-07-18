"""``Tag`` and its many-to-many association with
:class:`~cerebrum.infrastructure.database.models.document.Document` —
CIS Phase 2 Prompt 1's free-form Tags. Distinct from
:class:`~cerebrum.infrastructure.database.models.label.Label`: a Tag is
workspace-scoped free text with no structure beyond its name; a Label
carries a color and is meant for a smaller, curated taxonomy — see that
module's docstring.
"""

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Tag(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("workspace_id", "name"),)

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))


class DocumentTag(Base):
    """A pure many-to-many association — no surrogate ID, matching
    :class:`~cerebrum.infrastructure.database.models.role.RolePermission`'s
    precedent for the same shape of relationship.
    """

    __tablename__ = "document_tags"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )
