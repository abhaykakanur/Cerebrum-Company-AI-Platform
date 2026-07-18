"""``Workspace``: the unit a
:class:`~cerebrum.infrastructure.database.models.membership.WorkspaceMembership`
grants a user a :class:`~cerebrum.infrastructure.database.models.role.Role`
in — see docs/architecture/security/multi-tenancy-guide.md.
"""

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Workspace(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A slug is unique within its Organization, not globally — two
    different organizations may each have a "default" workspace.
    """

    __tablename__ = "workspaces"
    __table_args__ = (UniqueConstraint("organization_id", "slug"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255))
