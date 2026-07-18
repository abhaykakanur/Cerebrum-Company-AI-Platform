"""``Role``, ``Permission``, and the ``RolePermission`` association
between them — the RBAC framework's storage. No business permission is
seeded here (no ``INSERT`` of e.g. ``"documents:read"``) — see CIS Phase
1 Prompt 5's "No business permissions yet" scope. A future domain
inserts its own permission codes as it defines the actions it protects.
"""

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Role(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """``organization_id`` is nullable: ``NULL`` marks a system-wide role
    (e.g. a future platform-admin role) available to every organization;
    a non-``NULL`` value marks an organization-defined custom role.
    """

    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("organization_id", "name"),)

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100))


class Permission(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """``code`` is a stable, human-readable identifier (e.g.
    ``"workspace:read"``) — the same string a future
    ``require_permission(code)`` route dependency checks against, per
    docs/architecture/security/rbac-guide.md.
    """

    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)


class RolePermission(Base):
    """A pure many-to-many association — no surrogate ID or timestamps
    of its own, since the relationship itself has no independent
    lifecycle worth auditing beyond its existence.
    """

    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )
