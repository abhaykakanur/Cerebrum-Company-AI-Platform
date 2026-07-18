"""``Folder``: a hierarchical container for
:class:`~cerebrum.infrastructure.database.models.document.Document`
rows within one
:class:`~cerebrum.infrastructure.database.models.workspace.Workspace` —
CIS Phase 2 Prompt 1's Folder System. Self-referential via ``parent_id``;
``parent_id IS NULL`` marks a workspace-root folder.
"""

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    AuditFieldsMixin,
    OptimisticLockMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Folder(
    Base,
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    SoftDeleteMixin,
    AuditFieldsMixin,
    OptimisticLockMixin,
):
    """A folder's name is unique among its siblings (same workspace,
    same parent) — see
    cerebrum.application.knowledge.folder_service.FolderService for the
    duplicate-name/hierarchy validation this table's constraint alone
    cannot fully express (e.g. "no folder may be moved into its own
    descendant").
    """

    __tablename__ = "folders"
    __table_args__ = (UniqueConstraint("workspace_id", "parent_id", "name"),)

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("folders.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255))
