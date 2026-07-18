"""``Organization``: the tenant boundary. Every
:class:`~cerebrum.infrastructure.database.models.user.User` and
:class:`~cerebrum.infrastructure.database.models.workspace.Workspace`
belongs to exactly one — see
docs/architecture/security/multi-tenancy-guide.md for why this codebase
treats Organization, not Workspace, as the tenant-isolation boundary.
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Organization(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """No business profile data (billing plan, logo, settings) — see
    this package's ``__init__.py`` docstring.
    """

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
