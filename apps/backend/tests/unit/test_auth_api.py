"""HTTP-level proof of CIS Phase 1 Prompt 5's acceptance criteria: "Users
can authenticate", "JWT validation works", "Refresh flow works", "RBAC
protects routes", "Audit events are generated" — exercised through the
real middleware pipeline (cerebrum.middleware.authentication,
cerebrum.middleware.request_context, cerebrum.core.exception_handlers),
not just the application services directly (see
test_authentication_service.py/test_authorization_service.py for that).

Test functions are ``async def`` — pytest-asyncio (mode=auto, see root
pyproject.toml) awaits them directly — purely so they can ``await`` the
async ``db_session`` fixture to seed data and inspect the database.
``TestClient``'s ``.get()``/``.post()`` calls are synchronous regardless
and work identically from an async test body.
"""

import pytest
from _auth_factories import SeededTenant, seed_tenant_with_user
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.config.security import SecuritySettings
from cerebrum.infrastructure.database.models.audit import AuditEvent, AuditEventType
from cerebrum.infrastructure.security.password import PasswordHasher

pytestmark = pytest.mark.unit


@pytest.fixture
def hasher() -> PasswordHasher:
    return PasswordHasher(SecuritySettings())


async def _seed(
    db_session: AsyncSession, hasher: PasswordHasher, **kwargs: str
) -> SeededTenant:
    return await seed_tenant_with_user(db_session, hasher, **kwargs)


async def test_login_returns_oauth2_shaped_token_response(
    db_client: TestClient, db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    tenant = await _seed(db_session, hasher)

    response = db_client.post(
        "/api/v1/auth/login",
        data={"username": tenant.user_email, "password": tenant.user_password},
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "access_token",
        "refresh_token",
        "token_type",
        "expires_in",
    }
    assert body["token_type"] == "bearer"


async def test_login_with_wrong_password_returns_401_with_standard_envelope(
    db_client: TestClient, db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    tenant = await _seed(db_session, hasher)

    response = db_client.post(
        "/api/v1/auth/login", data={"username": tenant.user_email, "password": "wrong"}
    )

    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error_code"] == "AuthenticationException"
    assert "request_id" in body


async def test_me_without_a_token_returns_401(db_client: TestClient) -> None:
    response = db_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error_code"] == "AuthenticationException"


async def test_me_with_a_garbage_token_returns_401_with_a_populated_request_id(
    db_client: TestClient,
) -> None:
    """Exercises the specific fix in cerebrum.core.exception_handlers's
    ``_identifiers`` fallback: AuthenticationMiddleware runs before
    RequestContextMiddleware binds its contextvar, so the request_id
    must come from ``request.state`` instead, not be "unknown".
    """
    response = db_client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401
    body = response.json()
    assert body["error_code"] == "InvalidTokenException"
    assert body["request_id"] != "unknown"
    assert response.headers["X-Request-ID"] == body["request_id"]


async def test_full_login_me_refresh_logout_cycle(
    db_client: TestClient, db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    tenant = await _seed(db_session, hasher)

    login = db_client.post(
        "/api/v1/auth/login",
        data={"username": tenant.user_email, "password": tenant.user_password},
    )
    tokens = login.json()

    me = db_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == tenant.user_email

    refreshed = db_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200
    new_tokens = refreshed.json()
    assert new_tokens["access_token"] != tokens["access_token"]

    # The old refresh token no longer works — rotation revoked it.
    stale_refresh = db_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert stale_refresh.status_code == 401

    logout = db_client.post(
        "/api/v1/auth/logout", json={"refresh_token": new_tokens["refresh_token"]}
    )
    assert logout.status_code == 204

    post_logout_refresh = db_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]}
    )
    assert post_logout_refresh.status_code == 401


async def test_successful_login_is_recorded_as_an_audit_event(
    db_client: TestClient, db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    tenant = await _seed(db_session, hasher)

    response = db_client.post(
        "/api/v1/auth/login",
        data={"username": tenant.user_email, "password": tenant.user_password},
    )
    assert response.status_code == 200

    result = await db_session.execute(
        select(AuditEvent).where(AuditEvent.event_type == AuditEventType.LOGIN.value)
    )
    events = list(result.scalars())
    assert len(events) == 1
    assert events[0].user_id == tenant.user_id


async def test_auth_responses_are_not_cached(
    db_client: TestClient, db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    """Security headers refinement: token-bearing responses must never
    be cached — see cerebrum.middleware.security_headers.
    """
    tenant = await _seed(db_session, hasher)

    response = db_client.post(
        "/api/v1/auth/login",
        data={"username": tenant.user_email, "password": tenant.user_password},
    )
    assert response.headers["Cache-Control"] == "no-store"


async def test_docs_still_render_alongside_the_auth_router(
    db_client: TestClient,
) -> None:
    response = db_client.get("/api/v1/docs")
    assert response.status_code == 200


class TestRoutePermissionProtection:
    """Mounts a throwaway protected route to prove
    cerebrum.dependencies.auth.require_permission works end-to-end over
    HTTP — no real business route exists yet to hang this off of (CIS
    Phase 1 Prompt 5's "No business permissions yet" scope), so the
    dependency itself is what's under test here, using the same pattern
    a future business route will.
    """

    @pytest.fixture(autouse=True)
    def _mount_protected_route(self, app: FastAPI) -> None:
        from cerebrum.dependencies.auth import require_permission

        @app.get(
            "/api/v1/_test_protected",
            dependencies=[Depends(require_permission("documents:read"))],
        )
        async def _protected() -> dict[str, bool]:
            return {"ok": True}

    async def test_protected_route_without_a_workspace_header_returns_422(
        self, db_client: TestClient, db_session: AsyncSession, hasher: PasswordHasher
    ) -> None:
        tenant = await _seed(db_session, hasher)
        login = db_client.post(
            "/api/v1/auth/login",
            data={"username": tenant.user_email, "password": tenant.user_password},
        )
        access_token = login.json()["access_token"]

        response = db_client.get(
            "/api/v1/_test_protected",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert (
            response.status_code == 422
        )  # ValidationException — missing X-Workspace-ID

    async def test_protected_route_grants_access_with_the_right_permission(
        self, db_client: TestClient, db_session: AsyncSession, hasher: PasswordHasher
    ) -> None:
        tenant = await _seed(db_session, hasher, permission_code="documents:read")
        login = db_client.post(
            "/api/v1/auth/login",
            data={"username": tenant.user_email, "password": tenant.user_password},
        )
        access_token = login.json()["access_token"]

        response = db_client.get(
            "/api/v1/_test_protected",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Workspace-ID": str(tenant.workspace_id),
            },
        )
        assert response.status_code == 200

    async def test_protected_route_denies_access_without_the_permission(
        self, db_client: TestClient, db_session: AsyncSession, hasher: PasswordHasher
    ) -> None:
        tenant = await _seed(db_session, hasher, permission_code="documents:write")
        login = db_client.post(
            "/api/v1/auth/login",
            data={"username": tenant.user_email, "password": tenant.user_password},
        )
        access_token = login.json()["access_token"]

        response = db_client.get(
            "/api/v1/_test_protected",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Workspace-ID": str(tenant.workspace_id),
            },
        )
        assert response.status_code == 403
        assert response.json()["error_code"] == "PermissionDeniedException"
