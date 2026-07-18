"""Test-only data factories for the Identity & Security models — not a
pytest fixture module (no ``test_`` prefix, not collected), just plain
async helpers test files import and call against their own ``db_session``
fixture, since different tests need different combinations (single-org,
multi-org for tenant isolation, with/without a granted permission).
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.membership import WorkspaceMembership
from cerebrum.infrastructure.database.models.organization import Organization
from cerebrum.infrastructure.database.models.role import (
    Permission,
    Role,
    RolePermission,
)
from cerebrum.infrastructure.database.models.user import User
from cerebrum.infrastructure.database.models.workspace import Workspace
from cerebrum.infrastructure.security.password import PasswordHasher


async def create_organization(
    session: AsyncSession, *, name: str = "Acme", slug: str = "acme"
) -> Organization:
    org = Organization(name=name, slug=slug)
    session.add(org)
    await session.flush()
    return org


async def create_workspace(
    session: AsyncSession,
    *,
    organization_id: UUID,
    name: str = "Default",
    slug: str = "default",
) -> Workspace:
    workspace = Workspace(organization_id=organization_id, name=name, slug=slug)
    session.add(workspace)
    await session.flush()
    return workspace


async def create_role(
    session: AsyncSession, *, organization_id: UUID | None, name: str = "member"
) -> Role:
    role = Role(organization_id=organization_id, name=name)
    session.add(role)
    await session.flush()
    return role


async def create_permission(
    session: AsyncSession,
    *,
    code: str = "documents:read",
    description: str | None = None,
) -> Permission:
    permission = Permission(code=code, description=description)
    session.add(permission)
    await session.flush()
    return permission


async def grant_permission_to_role(
    session: AsyncSession, *, role_id: UUID, permission_id: UUID
) -> None:
    session.add(RolePermission(role_id=role_id, permission_id=permission_id))
    await session.flush()


async def create_user(
    session: AsyncSession,
    *,
    organization_id: UUID,
    email: str,
    password: str,
    hasher: PasswordHasher,
    is_active: bool = True,
) -> User:
    user = User(
        organization_id=organization_id,
        email=email,
        hashed_password=hasher.hash(password),
        is_active=is_active,
    )
    session.add(user)
    await session.flush()
    return user


async def create_membership(
    session: AsyncSession, *, user_id: UUID, workspace_id: UUID, role_id: UUID
) -> WorkspaceMembership:
    membership = WorkspaceMembership(
        user_id=user_id, workspace_id=workspace_id, role_id=role_id
    )
    session.add(membership)
    await session.flush()
    return membership


@dataclass(frozen=True, slots=True)
class SeededTenant:
    """One organization, one workspace, one user who is a member of it
    with one role holding one permission — the common case most
    authentication/authorization tests need.
    """

    organization_id: UUID
    workspace_id: UUID
    role_id: UUID
    user_id: UUID
    user_email: str
    user_password: str


async def seed_tenant_with_user(
    session: AsyncSession,
    hasher: PasswordHasher,
    *,
    email: str = "alice@example.com",
    password: str = "CorrectHorse123!",
    permission_code: str = "documents:read",
    organization_slug: str = "acme",
) -> SeededTenant:
    org = await create_organization(session, slug=organization_slug)
    workspace = await create_workspace(session, organization_id=org.id)
    role = await create_role(session, organization_id=org.id)
    permission = await create_permission(session, code=permission_code)
    await grant_permission_to_role(
        session, role_id=role.id, permission_id=permission.id
    )
    user = await create_user(
        session, organization_id=org.id, email=email, password=password, hasher=hasher
    )
    await create_membership(
        session, user_id=user.id, workspace_id=workspace.id, role_id=role.id
    )
    await session.commit()

    return SeededTenant(
        organization_id=org.id,
        workspace_id=workspace.id,
        role_id=role.id,
        user_id=user.id,
        user_email=email,
        user_password=password,
    )
