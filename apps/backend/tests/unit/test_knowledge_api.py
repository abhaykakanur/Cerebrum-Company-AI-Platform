"""Proves CIS Phase 2 Prompt 1's acceptance criteria "CRUD operations
function", "Tenant isolation enforced", and "RBAC enforced" through the
real HTTP/middleware pipeline — the same style as
test_auth_api.py/test_request_context_dependencies.py.
"""

import uuid
from dataclasses import dataclass

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
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.config.security import SecuritySettings
from cerebrum.infrastructure.database.models.role import Permission
from cerebrum.infrastructure.security.password import PasswordHasher

pytestmark = pytest.mark.unit

_ALL_PERMISSIONS = [
    "folders:read",
    "folders:write",
    "folders:delete",
    "documents:read",
    "documents:write",
    "documents:delete",
    "tags:read",
    "tags:write",
    "labels:read",
    "labels:write",
    "collections:read",
    "collections:write",
]


@dataclass(frozen=True, slots=True)
class _Tenant:
    organization_id: uuid.UUID
    workspace_id: uuid.UUID
    user_email: str
    user_password: str


@pytest.fixture
def hasher() -> PasswordHasher:
    return PasswordHasher(SecuritySettings())


async def _get_or_create_permission(session: AsyncSession, *, code: str) -> Permission:
    """``Permission.code`` is globally unique (shared across every
    organization — see
    cerebrum.infrastructure.database.models.role.Permission's docstring),
    so seeding more than one tenant in the same test must reuse an
    already-created permission rather than re-``INSERT``-ing the same
    code.
    """
    existing = await session.execute(select(Permission).where(Permission.code == code))
    permission = existing.scalar_one_or_none()
    if permission is not None:
        return permission
    return await create_permission(session, code=code)


async def _seed_full_access_tenant(
    session: AsyncSession, hasher: PasswordHasher, *, org_slug: str = "acme"
) -> _Tenant:
    org = await create_organization(session, slug=org_slug)
    workspace = await create_workspace(session, organization_id=org.id)
    role = await create_role(session, organization_id=org.id)
    for code in _ALL_PERMISSIONS:
        permission = await _get_or_create_permission(session, code=code)
        await grant_permission_to_role(
            session, role_id=role.id, permission_id=permission.id
        )
    user = await create_user(
        session,
        organization_id=org.id,
        email=f"alice@{org_slug}.example",
        password="CorrectHorse123!",
        hasher=hasher,
    )
    await create_membership(
        session, user_id=user.id, workspace_id=workspace.id, role_id=role.id
    )
    await session.commit()
    return _Tenant(
        organization_id=org.id,
        workspace_id=workspace.id,
        user_email=user.email,
        user_password="CorrectHorse123!",
    )


def _login(client: TestClient, tenant: _Tenant) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": tenant.user_email, "password": tenant.user_password},
    )
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    return {
        "Authorization": f"Bearer {access_token}",
        "X-Workspace-ID": str(tenant.workspace_id),
    }


async def test_folder_and_document_crud_roundtrip(
    db_client: TestClient, db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    tenant = await _seed_full_access_tenant(db_session, hasher)
    headers = _login(db_client, tenant)

    folder_resp = db_client.post(
        "/api/v1/folders", json={"name": "Reports"}, headers=headers
    )
    assert folder_resp.status_code == 201, folder_resp.text
    folder_id = folder_resp.json()["data"]["id"]

    doc_resp = db_client.post(
        "/api/v1/documents",
        json={"folder_id": folder_id, "name": "Q1.pdf"},
        headers=headers,
    )
    assert doc_resp.status_code == 201, doc_resp.text
    document = doc_resp.json()["data"]
    assert document["name"] == "Q1.pdf"
    assert document["status"] == "draft"
    document_id = document["id"]

    get_resp = db_client.get(f"/api/v1/documents/{document_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["folder_id"] == folder_id

    rename_resp = db_client.patch(
        f"/api/v1/documents/{document_id}",
        json={"name": "Q1-final.pdf"},
        headers=headers,
    )
    assert rename_resp.status_code == 200
    assert rename_resp.json()["data"]["name"] == "Q1-final.pdf"

    delete_resp = db_client.delete(f"/api/v1/documents/{document_id}", headers=headers)
    assert delete_resp.status_code == 204

    after_delete = db_client.get(f"/api/v1/documents/{document_id}", headers=headers)
    assert after_delete.status_code == 404

    restore_resp = db_client.post(
        f"/api/v1/documents/{document_id}/restore", headers=headers
    )
    assert restore_resp.status_code == 200
    assert restore_resp.json()["data"]["is_deleted"] is False


async def test_document_version_lifecycle(
    db_client: TestClient, db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    tenant = await _seed_full_access_tenant(db_session, hasher)
    headers = _login(db_client, tenant)

    doc_resp = db_client.post(
        "/api/v1/documents", json={"name": "Report.pdf"}, headers=headers
    )
    document_id = doc_resp.json()["data"]["id"]

    version_body = {
        "version_type": "major",
        "mime_type": "application/pdf",
        "file_size_bytes": 2048,
        "sha256_checksum": "a" * 64,
        "storage_path": "ws/report/v1.pdf",
        "original_filename": "Report.pdf",
        "uploaded_filename": "report-uuid.pdf",
        "uploaded_at": "2026-01-01T00:00:00Z",
    }
    v1_resp = db_client.post(
        f"/api/v1/documents/{document_id}/versions", json=version_body, headers=headers
    )
    assert v1_resp.status_code == 201, v1_resp.text
    v1 = v1_resp.json()["data"]
    assert v1["version_number"] == 1
    assert v1["is_current"] is True

    v2_body = {**version_body, "version_type": "minor", "sha256_checksum": "b" * 64}
    v2_resp = db_client.post(
        f"/api/v1/documents/{document_id}/versions", json=v2_body, headers=headers
    )
    v2 = v2_resp.json()["data"]
    assert v2["version_number"] == 2

    document_after = db_client.get(
        f"/api/v1/documents/{document_id}", headers=headers
    ).json()["data"]
    assert document_after["current_version_id"] == v2["id"]
    assert document_after["status"] == "uploaded"

    restore_resp = db_client.post(
        f"/api/v1/documents/{document_id}/versions/{v1['id']}/restore", headers=headers
    )
    assert restore_resp.status_code == 200
    assert restore_resp.json()["data"]["is_current"] is True

    metadata_resp = db_client.get(
        f"/api/v1/documents/{document_id}/versions/{v1['id']}/metadata", headers=headers
    )
    assert metadata_resp.status_code == 200
    assert metadata_resp.json()["data"]["sha256_checksum"] == "a" * 64


async def test_tenant_isolation_a_document_from_another_org_is_not_found(
    db_client: TestClient, db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    tenant_a = await _seed_full_access_tenant(db_session, hasher, org_slug="org-a")
    tenant_b = await _seed_full_access_tenant(db_session, hasher, org_slug="org-b")
    headers_a = _login(db_client, tenant_a)
    headers_b = _login(db_client, tenant_b)

    doc_resp = db_client.post(
        "/api/v1/documents", json={"name": "Secret.pdf"}, headers=headers_a
    )
    document_id = doc_resp.json()["data"]["id"]

    cross_tenant_resp = db_client.get(
        f"/api/v1/documents/{document_id}", headers=headers_b
    )
    assert cross_tenant_resp.status_code == 404


async def test_rbac_denies_document_creation_without_permission(
    db_client: TestClient, db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    org = await create_organization(db_session, slug="no-perms")
    workspace = await create_workspace(db_session, organization_id=org.id)
    role = await create_role(db_session, organization_id=org.id)
    # Grant only folders:read — not documents:write.
    permission = await create_permission(db_session, code="folders:read")
    await grant_permission_to_role(
        db_session, role_id=role.id, permission_id=permission.id
    )
    user = await create_user(
        db_session,
        organization_id=org.id,
        email="bob@no-perms.example",
        password="CorrectHorse123!",
        hasher=hasher,
    )
    await create_membership(
        db_session, user_id=user.id, workspace_id=workspace.id, role_id=role.id
    )
    await db_session.commit()
    tenant = _Tenant(
        organization_id=org.id,
        workspace_id=workspace.id,
        user_email=user.email,
        user_password="CorrectHorse123!",
    )
    headers = _login(db_client, tenant)

    response = db_client.post(
        "/api/v1/documents", json={"name": "X.pdf"}, headers=headers
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "PermissionDeniedException"


async def test_folder_hierarchy_move_rejects_cycle_over_http(
    db_client: TestClient, db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    tenant = await _seed_full_access_tenant(db_session, hasher, org_slug="cycle-org")
    headers = _login(db_client, tenant)

    parent = db_client.post(
        "/api/v1/folders", json={"name": "Parent"}, headers=headers
    ).json()["data"]
    child = db_client.post(
        "/api/v1/folders",
        json={"name": "Child", "parent_id": parent["id"]},
        headers=headers,
    ).json()["data"]

    response = db_client.post(
        f"/api/v1/folders/{parent['id']}/move",
        json={"new_parent_id": child["id"]},
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "ValidationException"


async def test_collections_bulk_add_documents(
    db_client: TestClient, db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    tenant = await _seed_full_access_tenant(db_session, hasher, org_slug="bulk-org")
    headers = _login(db_client, tenant)

    doc_a = db_client.post(
        "/api/v1/documents", json={"name": "A.pdf"}, headers=headers
    ).json()["data"]
    doc_b = db_client.post(
        "/api/v1/documents", json={"name": "B.pdf"}, headers=headers
    ).json()["data"]
    collection = db_client.post(
        "/api/v1/collections", json={"name": "Q1", "description": None}, headers=headers
    ).json()["data"]

    response = db_client.post(
        f"/api/v1/collections/{collection['id']}/documents/bulk",
        json={"document_ids": [doc_a["id"], doc_b["id"]]},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["succeeded"] == 2

    listing = db_client.get(
        f"/api/v1/collections/{collection['id']}/documents", headers=headers
    )
    assert listing.status_code == 200
    assert set(listing.json()["data"]) == {doc_a["id"], doc_b["id"]}
