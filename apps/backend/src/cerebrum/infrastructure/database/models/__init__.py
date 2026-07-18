"""Foundational ORM models for the Identity & Security platform (CIS
Phase 1 Prompt 5): ``Organization``, ``Workspace``, ``User``, ``Role``,
``Permission``, ``RolePermission``, ``WorkspaceMembership``, ``APIKey``,
``UserSession``, ``AuditEvent`` — one module each, in this package.

Deliberately minimal — "No business profile data" (CIS Phase 1 Prompt
5's scope): no name/avatar/bio/preferences on ``User``, no seeded
business permissions, no relationship-heavy object graph. These are the
tables the Identity & Security *platform* needs to function; the richer
Identity domain (aggregates, invariants, domain events) is Phase 2 work
per docs/architecture/specification/110_Implementation_Roadmap.md.

Every model is imported here so
``cerebrum.infrastructure.database.base.Base.metadata`` sees all of them
— Alembic's ``env.py`` imports ``Base``, not this package, but a model
defined and never imported anywhere is invisible to
``Base.metadata.create_all``/autogenerate, so this import is load-bearing.
"""

from cerebrum.infrastructure.database.models.api_key import APIKey
from cerebrum.infrastructure.database.models.audit import AuditEvent, AuditEventType
from cerebrum.infrastructure.database.models.membership import WorkspaceMembership
from cerebrum.infrastructure.database.models.organization import Organization
from cerebrum.infrastructure.database.models.role import (
    Permission,
    Role,
    RolePermission,
)
from cerebrum.infrastructure.database.models.session import UserSession
from cerebrum.infrastructure.database.models.user import User
from cerebrum.infrastructure.database.models.workspace import Workspace

__all__ = [
    "APIKey",
    "AuditEvent",
    "AuditEventType",
    "WorkspaceMembership",
    "Organization",
    "Permission",
    "Role",
    "RolePermission",
    "UserSession",
    "User",
    "Workspace",
]
