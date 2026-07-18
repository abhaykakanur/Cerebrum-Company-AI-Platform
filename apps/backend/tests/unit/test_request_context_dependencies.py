"""Proves CIS Phase 1 Prompt 6's Request Context dependencies —
Tenant, Request ID, Correlation ID, and Permissions — resolve correctly
over HTTP, through the real middleware pipeline. Current User and Current
Workspace already have HTTP-level coverage via test_auth_api.py's
``/me`` and ``TestRoutePermissionProtection``; this module covers what
CIS Phase 1 Prompt 6 adds in cerebrum.dependencies.request_context.

Mounts a throwaway route, following test_auth_api.py's
``TestRoutePermissionProtection`` precedent: no real business route
exists yet to hang this off of.
"""

import pytest
from _auth_factories import seed_tenant_with_user
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.config.security import SecuritySettings
from cerebrum.infrastructure.security.password import PasswordHasher

pytestmark = pytest.mark.unit


@pytest.fixture
def hasher() -> PasswordHasher:
    return PasswordHasher(SecuritySettings())


@pytest.fixture(autouse=True)
def _mount_context_route(app: FastAPI) -> None:
    from cerebrum.dependencies.request_context import (
        CorrelationIdDep,
        CurrentPermissionsDep,
        RequestIdDep,
        TenantIdDep,
    )

    @app.get("/api/v1/_test_context")
    async def _context(
        request_id: RequestIdDep,
        correlation_id: CorrelationIdDep,
        tenant_id: TenantIdDep,
        permissions: CurrentPermissionsDep,
    ) -> dict[str, object]:
        return {
            "request_id": request_id,
            "correlation_id": correlation_id,
            "tenant_id": str(tenant_id),
            "permissions": sorted(permissions),
        }


async def test_context_dependencies_resolve_over_http(
    db_client: TestClient, db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    tenant = await seed_tenant_with_user(
        db_session, hasher, permission_code="documents:read"
    )
    login = db_client.post(
        "/api/v1/auth/login",
        data={"username": tenant.user_email, "password": tenant.user_password},
    )
    access_token = login.json()["access_token"]

    response = db_client.get(
        "/api/v1/_test_context",
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-Workspace-ID": str(tenant.workspace_id),
            "X-Correlation-ID": "test-correlation-xyz",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert body["correlation_id"] == "test-correlation-xyz"
    assert body["tenant_id"] == str(tenant.organization_id)
    assert body["permissions"] == ["documents:read"]


async def test_tenant_id_is_derived_from_the_token_never_a_header(
    db_client: TestClient, db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    """docs/architecture/specification/81_API_Standards.md's Request
    Standards: Tenant ID is "never client-supplied as an override" — an
    attempt to spoof it via a header has no effect.
    """
    tenant = await seed_tenant_with_user(db_session, hasher)
    login = db_client.post(
        "/api/v1/auth/login",
        data={"username": tenant.user_email, "password": tenant.user_password},
    )
    access_token = login.json()["access_token"]
    spoofed_tenant_id = "00000000-0000-0000-0000-000000000000"

    response = db_client.get(
        "/api/v1/_test_context",
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-Workspace-ID": str(tenant.workspace_id),
            "X-Tenant-ID": spoofed_tenant_id,
        },
    )

    assert response.json()["tenant_id"] == str(tenant.organization_id)
    assert response.json()["tenant_id"] != spoofed_tenant_id


async def test_context_route_without_authentication_returns_401(
    db_client: TestClient,
) -> None:
    response = db_client.get("/api/v1/_test_context")
    assert response.status_code == 401
