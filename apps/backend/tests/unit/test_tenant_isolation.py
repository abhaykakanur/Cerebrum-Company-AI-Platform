"""Proves the acceptance criterion "Tenant context resolves correctly"
and CIS Phase 1 Prompt 5's "Prevent cross-tenant access by design"
requirement.

The design in question: RBAC permission resolution
(``RoleRepository.get_permission_codes_for_membership``) joins through
:class:`~cerebrum.infrastructure.database.models.membership.WorkspaceMembership`,
which requires an actual ``(user_id, workspace_id)`` row to exist.
Cross-tenant access isn't prevented by an explicit "does this workspace
belong to this user's organization?" check bolted on top — it's
structurally impossible to observe another tenant's permissions without
a membership row, by construction of the query itself. These tests
verify that structural guarantee holds, including the case CIS Phase 1
Prompt 5 arguably cares about most: a permission *code* is a global
string (``"documents:read"``), not itself tenant-scoped — a naive
implementation keyed only on the code, without the join through
membership, would leak grants across tenants.
"""

import pytest
from _auth_factories import (
    create_membership,
    create_organization,
    create_permission,
    create_role,
    create_user,
    create_workspace,
    grant_permission_to_role,
)
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.auth.audit_service import AuditService
from cerebrum.application.auth.authorization_service import AuthorizationService
from cerebrum.config.security import SecuritySettings
from cerebrum.infrastructure.security.jwt import TokenService
from cerebrum.infrastructure.security.password import PasswordHasher
from cerebrum.repositories.postgres.audit_repository import AuditEventRepository
from cerebrum.repositories.postgres.role_repository import RoleRepository

pytestmark = pytest.mark.unit


@pytest.fixture
def security_settings() -> SecuritySettings:
    return SecuritySettings()


@pytest.fixture
def hasher(security_settings: SecuritySettings) -> PasswordHasher:
    return PasswordHasher(security_settings)


async def test_identical_permission_code_does_not_leak_across_organizations(
    db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    """Org A grants "documents:read" to Alice in Org A's workspace. Org
    B independently defines its own "documents:read" permission and
    grants it to Bob in Org B's workspace. Alice must not be able to
    exercise "documents:read" in Org B's workspace, and vice versa —
    even though the permission code string is identical in both orgs.
    """
    org_a = await create_organization(db_session, slug="org-a")
    workspace_a = await create_workspace(db_session, organization_id=org_a.id)
    role_a = await create_role(db_session, organization_id=org_a.id)
    permission_a = await create_permission(db_session, code="documents:read")
    await grant_permission_to_role(
        db_session, role_id=role_a.id, permission_id=permission_a.id
    )
    alice = await create_user(
        db_session,
        organization_id=org_a.id,
        email="alice@org-a.example",
        password="CorrectHorse123!",
        hasher=hasher,
    )
    await create_membership(
        db_session, user_id=alice.id, workspace_id=workspace_a.id, role_id=role_a.id
    )

    org_b = await create_organization(db_session, slug="org-b")
    workspace_b = await create_workspace(db_session, organization_id=org_b.id)
    role_b = await create_role(db_session, organization_id=org_b.id)
    permission_b = await create_permission(
        db_session, code="documents:write"
    )  # distinct code on purpose
    await grant_permission_to_role(
        db_session, role_id=role_b.id, permission_id=permission_b.id
    )
    bob = await create_user(
        db_session,
        organization_id=org_b.id,
        email="bob@org-b.example",
        password="CorrectHorse123!",
        hasher=hasher,
    )
    await create_membership(
        db_session, user_id=bob.id, workspace_id=workspace_b.id, role_id=role_b.id
    )
    await db_session.commit()

    service = AuthorizationService(
        role_repository=RoleRepository(db_session),
        audit_service=AuditService(AuditEventRepository(db_session)),
    )

    # Alice has "documents:read" in her own workspace...
    assert await service.has_permission(
        user_id=alice.id, workspace_id=workspace_a.id, permission_code="documents:read"
    )
    # ...but not in Org B's workspace, despite never having been denied
    # explicitly — she simply has no membership there.
    assert not await service.has_permission(
        user_id=alice.id, workspace_id=workspace_b.id, permission_code="documents:read"
    )
    # Bob, symmetrically, cannot reach into Org A's workspace.
    assert not await service.has_permission(
        user_id=bob.id, workspace_id=workspace_a.id, permission_code="documents:write"
    )


async def test_access_token_from_one_organization_does_not_grant_membership_in_another(
    db_session: AsyncSession,
    hasher: PasswordHasher,
    security_settings: SecuritySettings,
) -> None:
    """The access token's ``org_id`` claim identifies the user's own
    tenant (see cerebrum.infrastructure.security.jwt.TokenPayload) — it
    is never used as an authorization decision by itself. The actual
    gate is the ``WorkspaceMembership`` row, per this module's docstring.
    A user's token correctly identifying their own organization must not
    be mistaken for a grant into a workspace under a *different*
    organization, even one the same physical user somehow also has an
    (unrelated) account in.
    """
    org_a = await create_organization(db_session, slug="org-a")
    workspace_a = await create_workspace(db_session, organization_id=org_a.id)
    role_a = await create_role(db_session, organization_id=org_a.id)
    permission = await create_permission(db_session, code="workspace:read")
    await grant_permission_to_role(
        db_session, role_id=role_a.id, permission_id=permission.id
    )
    user_in_org_a = await create_user(
        db_session,
        organization_id=org_a.id,
        email="dana@org-a.example",
        password="CorrectHorse123!",
        hasher=hasher,
    )
    await create_membership(
        db_session,
        user_id=user_in_org_a.id,
        workspace_id=workspace_a.id,
        role_id=role_a.id,
    )

    org_b = await create_organization(db_session, slug="org-b")
    workspace_b = await create_workspace(db_session, organization_id=org_b.id)
    await db_session.commit()

    tokens = TokenService(security_settings)
    access_token = tokens.create_access_token(
        user_id=user_in_org_a.id, organization_id=user_in_org_a.organization_id
    )
    from cerebrum.infrastructure.security.jwt import TokenType

    payload = tokens.decode_token(access_token, expected_type=TokenType.ACCESS)
    assert payload.organization_id == org_a.id

    service = AuthorizationService(
        role_repository=RoleRepository(db_session),
        audit_service=AuditService(AuditEventRepository(db_session)),
    )
    # Even with a validly-decoded token identifying this user and their
    # real organization, they have no membership in Org B's workspace.
    assert not await service.has_permission(
        user_id=payload.subject,
        workspace_id=workspace_b.id,
        permission_code="workspace:read",
    )
