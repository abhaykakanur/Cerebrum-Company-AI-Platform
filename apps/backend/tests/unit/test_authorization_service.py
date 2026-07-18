"""Proves the acceptance criteria "RBAC protects routes" and "Permission
checking" from CIS Phase 1 Prompt 5.
"""

import pytest
from _auth_factories import (
    create_membership,
    create_organization,
    create_role,
    create_user,
    create_workspace,
    seed_tenant_with_user,
)
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.auth.audit_service import AuditService
from cerebrum.application.auth.authorization_service import AuthorizationService
from cerebrum.config.security import SecuritySettings
from cerebrum.infrastructure.security.password import PasswordHasher
from cerebrum.repositories.postgres.audit_repository import AuditEventRepository
from cerebrum.repositories.postgres.role_repository import RoleRepository
from cerebrum.shared.errors.exceptions import PermissionDeniedException

pytestmark = pytest.mark.unit


@pytest.fixture
def hasher() -> PasswordHasher:
    return PasswordHasher(SecuritySettings())


def _build_service(session: AsyncSession) -> AuthorizationService:
    return AuthorizationService(
        role_repository=RoleRepository(session),
        audit_service=AuditService(AuditEventRepository(session)),
    )


async def test_has_permission_is_true_for_a_granted_permission(
    db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    tenant = await seed_tenant_with_user(
        db_session, hasher, permission_code="documents:read"
    )
    service = _build_service(db_session)

    assert await service.has_permission(
        user_id=tenant.user_id,
        workspace_id=tenant.workspace_id,
        permission_code="documents:read",
    )


async def test_has_permission_is_false_for_an_ungranted_permission(
    db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    tenant = await seed_tenant_with_user(
        db_session, hasher, permission_code="documents:read"
    )
    service = _build_service(db_session)

    assert not await service.has_permission(
        user_id=tenant.user_id,
        workspace_id=tenant.workspace_id,
        permission_code="documents:delete",
    )


async def test_has_permission_is_false_for_a_user_with_no_membership(
    db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    tenant = await seed_tenant_with_user(db_session, hasher)
    org = await create_organization(db_session, slug="other-org")
    other_workspace = await create_workspace(db_session, organization_id=org.id)
    await db_session.commit()
    service = _build_service(db_session)

    assert not await service.has_permission(
        user_id=tenant.user_id,
        workspace_id=other_workspace.id,
        permission_code="documents:read",
    )


async def test_require_permission_raises_for_a_missing_permission(
    db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    tenant = await seed_tenant_with_user(
        db_session, hasher, permission_code="documents:read"
    )
    service = _build_service(db_session)

    with pytest.raises(PermissionDeniedException) as exc_info:
        await service.require_permission(
            user_id=tenant.user_id,
            workspace_id=tenant.workspace_id,
            permission_code="documents:delete",
        )
    assert exc_info.value.context["permission_code"] == "documents:delete"


async def test_require_permission_does_not_raise_when_granted(
    db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    tenant = await seed_tenant_with_user(
        db_session, hasher, permission_code="documents:read"
    )
    service = _build_service(db_session)

    await service.require_permission(
        user_id=tenant.user_id,
        workspace_id=tenant.workspace_id,
        permission_code="documents:read",
    )  # must not raise


async def test_permission_denial_is_recorded_as_an_audit_event(
    db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    from sqlalchemy import select

    from cerebrum.infrastructure.database.models.audit import AuditEvent, AuditEventType

    tenant = await seed_tenant_with_user(
        db_session, hasher, permission_code="documents:read"
    )
    service = _build_service(db_session)

    with pytest.raises(PermissionDeniedException):
        await service.require_permission(
            user_id=tenant.user_id,
            workspace_id=tenant.workspace_id,
            permission_code="documents:delete",
        )
    await db_session.commit()

    result = await db_session.execute(
        select(AuditEvent).where(
            AuditEvent.event_type == AuditEventType.PERMISSION_DENIED.value
        )
    )
    events = list(result.scalars())
    assert len(events) == 1
    assert events[0].user_id == tenant.user_id
    assert events[0].workspace_id == tenant.workspace_id


async def test_two_roles_in_the_same_workspace_grant_different_permissions(
    db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    """Two distinct memberships (different roles) in the same workspace
    must resolve independently — one user's elevated permission must
    not leak to another user with a lesser role in the same workspace.
    """
    from _auth_factories import create_permission, grant_permission_to_role

    org = await create_organization(db_session)
    workspace = await create_workspace(db_session, organization_id=org.id)
    admin_role = await create_role(db_session, organization_id=org.id, name="admin")
    member_role = await create_role(db_session, organization_id=org.id, name="member")
    read_permission = await create_permission(db_session, code="documents:read")
    delete_permission = await create_permission(db_session, code="documents:delete")
    await grant_permission_to_role(
        db_session, role_id=admin_role.id, permission_id=read_permission.id
    )
    await grant_permission_to_role(
        db_session, role_id=admin_role.id, permission_id=delete_permission.id
    )
    await grant_permission_to_role(
        db_session, role_id=member_role.id, permission_id=read_permission.id
    )

    admin_user = await create_user(
        db_session,
        organization_id=org.id,
        email="admin@example.com",
        password="AdminPass123!",
        hasher=hasher,
    )
    member_user = await create_user(
        db_session,
        organization_id=org.id,
        email="member@example.com",
        password="MemberPass123!",
        hasher=hasher,
    )
    await create_membership(
        db_session,
        user_id=admin_user.id,
        workspace_id=workspace.id,
        role_id=admin_role.id,
    )
    await create_membership(
        db_session,
        user_id=member_user.id,
        workspace_id=workspace.id,
        role_id=member_role.id,
    )
    await db_session.commit()

    service = _build_service(db_session)
    assert await service.has_permission(
        user_id=admin_user.id,
        workspace_id=workspace.id,
        permission_code="documents:delete",
    )
    assert not await service.has_permission(
        user_id=member_user.id,
        workspace_id=workspace.id,
        permission_code="documents:delete",
    )
