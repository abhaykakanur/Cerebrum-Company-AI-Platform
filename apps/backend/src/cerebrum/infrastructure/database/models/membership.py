"""``WorkspaceMembership``: grants one
:class:`~cerebrum.infrastructure.database.models.user.User` one
:class:`~cerebrum.infrastructure.database.models.role.Role` within one
:class:`~cerebrum.infrastructure.database.models.workspace.Workspace` —
the join RBAC permission checks traverse (User → WorkspaceMembership →
Role → RolePermission → Permission). See
docs/architecture/security/rbac-guide.md and
docs/architecture/security/multi-tenancy-guide.md.
"""

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class WorkspaceMembership(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A user has at most one role per workspace — one membership row
    each. Membership in multiple workspaces means multiple rows.
    """

    __tablename__ = "workspace_memberships"
    __table_args__ = (UniqueConstraint("user_id", "workspace_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="RESTRICT")
    )
