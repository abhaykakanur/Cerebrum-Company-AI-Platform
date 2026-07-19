"""Creates the first Organization, Workspace, admin Role (granted every
known permission code), and User — the missing initialization step
between "migrations applied" and "someone can log in."

**Why this script exists:** `cerebrum.api.v1.auth` deliberately has no
registration endpoint (see that module's docstring and
`apps/frontend/README.md`'s Known Limitations) — accounts are
provisioned out-of-band by design, not by oversight. But nothing in this
repository actually performs that out-of-band provisioning: Alembic's
migrations create the `organizations`/`workspaces`/`roles`/
`permissions`/`users` tables (schema only, no rows), and the only place
that ever inserted a row into them was
`apps/backend/tests/unit/_auth_factories.py`, a test-only fixture
helper not reachable outside pytest. On a freshly migrated database
this means the `users` table is empty, so `POST /auth/login` correctly
rejects every credential with "Incorrect email or password." — not a
bug in the login code, a genuinely missing bootstrap step. This script
is that step, following the exact same
Organization/Workspace/Role/Permission/User/WorkspaceMembership
construction `_auth_factories.py` already established for tests,
just driven by real settings/PasswordHasher against a real database
instead of the test session fixture.

Prerequisites: PostgreSQL reachable and `alembic upgrade head` already
run (this script does not create tables).

Usage (from the repository root):
    uv run --project apps/backend python apps/backend/scripts/create_admin.py \\
        --email admin@example.com --password 'ChangeMe123!' \\
        --org-name "My Organization" --org-slug my-organization \\
        --workspace-name Default --workspace-slug default

Safe to re-run: an existing organization/workspace/role is reused rather
than duplicated (matched by slug/name); a user with the given email
already existing is treated as an error, not silently skipped, so you
don't accidentally believe a password was set when it wasn't.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.config.settings import get_settings
from cerebrum.infrastructure.database.engine import create_engine
from cerebrum.infrastructure.database.models.membership import WorkspaceMembership
from cerebrum.infrastructure.database.models.organization import Organization
from cerebrum.infrastructure.database.models.role import (
    Permission,
    Role,
    RolePermission,
)
from cerebrum.infrastructure.database.models.user import User
from cerebrum.infrastructure.database.models.workspace import Workspace
from cerebrum.infrastructure.database.session import create_session_factory
from cerebrum.infrastructure.security.password import (
    PasswordHasher,
    validate_password_policy,
)

# Every `require_permission("<code>")` call site in apps/backend/src/cerebrum/api/
# as of this script's writing — kept as a literal list, not derived from
# a shared catalog module, because no such catalog exists yet (each
# domain's routes define their own permission strings inline). Re-run
# `grep -rhoE 'require_permission\\("[a-z_]+:[a-z_]+"\\)' apps/backend/src/cerebrum/`
# to regenerate this list if a future domain adds new permission codes
# this script should also grant the bootstrap admin.
ALL_KNOWN_PERMISSIONS = sorted(
    {
        "ai:ask",
        "ai:read",
        "capsules:read",
        "capsules:write",
        "collections:read",
        "collections:write",
        "connectors:read",
        "connectors:write",
        "conversations:read",
        "conversations:write",
        "documents:delete",
        "documents:read",
        "documents:write",
        "entities:delete",
        "entities:read",
        "entities:write",
        "folders:delete",
        "folders:read",
        "folders:write",
        "graph:read",
        "labels:read",
        "labels:write",
        "relationships:delete",
        "relationships:read",
        "relationships:write",
        "search:read",
        "tags:read",
        "tags:write",
        "workflows:read",
        "workflows:write",
        "workspace:read",
    }
)


async def _get_or_create_organization(
    session: AsyncSession, *, name: str, slug: str
) -> Organization:
    existing = await session.scalar(
        select(Organization).where(Organization.slug == slug)
    )
    if existing is not None:
        return existing
    organization = Organization(name=name, slug=slug)
    session.add(organization)
    await session.flush()
    return organization


async def _get_or_create_workspace(
    session: AsyncSession, *, organization_id: uuid.UUID, name: str, slug: str
) -> Workspace:
    existing = await session.scalar(
        select(Workspace).where(
            Workspace.organization_id == organization_id, Workspace.slug == slug
        )
    )
    if existing is not None:
        return existing
    workspace = Workspace(organization_id=organization_id, name=name, slug=slug)
    session.add(workspace)
    await session.flush()
    return workspace


async def _get_or_create_admin_role(
    session: AsyncSession, *, organization_id: uuid.UUID
) -> Role:
    existing = await session.scalar(
        select(Role).where(
            Role.organization_id == organization_id, Role.name == "admin"
        )
    )
    if existing is not None:
        return existing
    role = Role(organization_id=organization_id, name="admin")
    session.add(role)
    await session.flush()
    return role


async def _get_or_create_permission(session: AsyncSession, *, code: str) -> Permission:
    existing = await session.scalar(select(Permission).where(Permission.code == code))
    if existing is not None:
        return existing
    permission = Permission(code=code)
    session.add(permission)
    await session.flush()
    return permission


async def _ensure_role_has_permission(
    session: AsyncSession, *, role_id: uuid.UUID, permission_id: uuid.UUID
) -> None:
    existing = await session.scalar(
        select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        )
    )
    if existing is None:
        session.add(RolePermission(role_id=role_id, permission_id=permission_id))


async def create_admin(
    *,
    email: str,
    password: str,
    org_name: str,
    org_slug: str,
    workspace_name: str,
    workspace_slug: str,
) -> None:
    settings = get_settings()
    validate_password_policy(password, settings.security)
    hasher = PasswordHasher(settings.security)

    engine = create_engine(settings.postgres.dsn)
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        existing_user = await session.scalar(select(User).where(User.email == email))
        if existing_user is not None:
            raise SystemExit(
                f"A user with email '{email}' already exists (id={existing_user.id}). "
                "Refusing to overwrite — delete that row first if you intend to "
                "recreate it, or choose a different --email."
            )

        organization = await _get_or_create_organization(
            session, name=org_name, slug=org_slug
        )
        workspace = await _get_or_create_workspace(
            session,
            organization_id=organization.id,
            name=workspace_name,
            slug=workspace_slug,
        )
        role = await _get_or_create_admin_role(session, organization_id=organization.id)
        for code in ALL_KNOWN_PERMISSIONS:
            permission = await _get_or_create_permission(session, code=code)
            await _ensure_role_has_permission(
                session, role_id=role.id, permission_id=permission.id
            )

        user = User(
            organization_id=organization.id,
            email=email,
            hashed_password=hasher.hash(password),
            is_active=True,
            is_verified=True,
        )
        session.add(user)
        await session.flush()

        session.add(
            WorkspaceMembership(
                user_id=user.id, workspace_id=workspace.id, role_id=role.id
            )
        )
        await session.commit()

        permission_count = len(ALL_KNOWN_PERMISSIONS)
        print("Created:")
        print(f"  organization: {organization.name} ({organization.slug})")
        print(f"    id: {organization.id}")
        print(f"  workspace:    {workspace.name} ({workspace.slug})")
        print(f"    id: {workspace.id}")
        print(f"  role:         {role.name} — {permission_count} permissions granted")
        print(f"  user:         {user.email}")
        print(f"    id: {user.id}")
        print()
        print("Sign in at the frontend's /login with the email/password you provided.")

    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--org-name", default="My Organization")
    parser.add_argument("--org-slug", default="my-organization")
    parser.add_argument("--workspace-name", default="Default")
    parser.add_argument("--workspace-slug", default="default")
    args = parser.parse_args()

    try:
        asyncio.run(
            create_admin(
                email=args.email,
                password=args.password,
                org_name=args.org_name,
                org_slug=args.org_slug,
                workspace_name=args.workspace_name,
                workspace_slug=args.workspace_slug,
            )
        )
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
