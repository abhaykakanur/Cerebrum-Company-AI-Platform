"""HTTP-level proof that CIS Phase 2 Prompt 3's extraction routes are
wired correctly (RBAC, response envelope) — same
``app.dependency_overrides`` pattern test_upload_api.py established for
``get_upload_service``/``get_processing_service``.
"""

import uuid
from datetime import UTC, datetime

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
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.config.security import SecuritySettings
from cerebrum.dependencies.knowledge import get_extraction_service
from cerebrum.infrastructure.database.models.document_extraction import (
    DocumentExtraction,
    ExtractionStatus,
)
from cerebrum.infrastructure.security.password import PasswordHasher
from cerebrum.shared.errors.exceptions import NotFoundException, ValidationException

pytestmark = pytest.mark.unit


@pytest.fixture
def hasher() -> PasswordHasher:
    return PasswordHasher(SecuritySettings())


async def _seed_full_access_tenant(session: AsyncSession, hasher: PasswordHasher):  # type: ignore[no-untyped-def]
    from sqlalchemy import select

    from cerebrum.infrastructure.database.models.role import Permission

    org = await create_organization(session, slug="acme")
    workspace = await create_workspace(session, organization_id=org.id)
    role = await create_role(session, organization_id=org.id)
    for code in ["documents:read", "documents:write"]:
        existing = await session.execute(
            select(Permission).where(Permission.code == code)
        )
        permission = existing.scalar_one_or_none()
        if permission is None:
            permission = await create_permission(session, code=code)
        await grant_permission_to_role(
            session, role_id=role.id, permission_id=permission.id
        )
    user = await create_user(
        session,
        organization_id=org.id,
        email="alice@acme.example",
        password="CorrectHorse123!",
        hasher=hasher,
    )
    await create_membership(
        session, user_id=user.id, workspace_id=workspace.id, role_id=role.id
    )
    await session.commit()
    return workspace.id, user


def _login(
    client: TestClient, *, email: str, password: str, workspace_id: uuid.UUID
) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", data={"username": email, "password": password}
    )
    assert response.status_code == 200
    return {
        "Authorization": f"Bearer {response.json()['access_token']}",
        "X-Workspace-ID": str(workspace_id),
    }


class _FakeExtractionService:
    def __init__(self) -> None:
        self.extraction = DocumentExtraction(
            id=uuid.uuid4(),
            document_version_id=uuid.uuid4(),
            processing_job_id=uuid.uuid4(),
            status=ExtractionStatus.COMPLETED.value,
            extracted_text="hello world",
            extracted_metadata={"line_count": 1},
            error_message=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    async def extract(self, version_id, *, workspace_id):  # type: ignore[no-untyped-def]
        return self.extraction

    async def get_for_version(self, version_id, *, workspace_id):  # type: ignore[no-untyped-def]
        return self.extraction

    async def retry(self, job_id, *, workspace_id):  # type: ignore[no-untyped-def]
        return self.extraction


class _NotFoundExtractionService:
    async def get_for_version(self, version_id, *, workspace_id):  # type: ignore[no-untyped-def]
        raise NotFoundException("No extraction result.")


class _RejectingRetryExtractionService:
    async def retry(self, job_id, *, workspace_id):  # type: ignore[no-untyped-def]
        raise ValidationException("Only a failed or cancelled job can be retried.")


async def test_extract_endpoint_returns_the_extraction_result(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    workspace_id, user = await _seed_full_access_tenant(db_session, hasher)
    headers = _login(
        db_client,
        email=user.email,
        password="CorrectHorse123!",
        workspace_id=workspace_id,
    )

    fake_service = _FakeExtractionService()
    app.dependency_overrides[get_extraction_service] = lambda: fake_service
    try:
        response = db_client.post(
            f"/api/v1/documents/{uuid.uuid4()}/versions/{uuid.uuid4()}/extract",
            headers=headers,
        )
    finally:
        del app.dependency_overrides[get_extraction_service]

    assert response.status_code == 201, response.text
    body = response.json()["data"]
    assert body["status"] == "completed"
    assert body["extracted_text"] == "hello world"


async def test_get_extraction_endpoint_returns_404_when_no_extraction_exists(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    workspace_id, user = await _seed_full_access_tenant(db_session, hasher)
    headers = _login(
        db_client,
        email=user.email,
        password="CorrectHorse123!",
        workspace_id=workspace_id,
    )

    app.dependency_overrides[get_extraction_service] = (
        lambda: _NotFoundExtractionService()
    )
    try:
        response = db_client.get(
            f"/api/v1/documents/{uuid.uuid4()}/versions/{uuid.uuid4()}/extraction",
            headers=headers,
        )
    finally:
        del app.dependency_overrides[get_extraction_service]

    assert response.status_code == 404


async def test_retry_extraction_endpoint_rejects_a_non_retryable_job(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    workspace_id, user = await _seed_full_access_tenant(db_session, hasher)
    headers = _login(
        db_client,
        email=user.email,
        password="CorrectHorse123!",
        workspace_id=workspace_id,
    )

    app.dependency_overrides[get_extraction_service] = (
        lambda: _RejectingRetryExtractionService()
    )
    try:
        response = db_client.post(
            f"/api/v1/documents/{uuid.uuid4()}/versions/{uuid.uuid4()}/extraction/retry/{uuid.uuid4()}",
            headers=headers,
        )
    finally:
        del app.dependency_overrides[get_extraction_service]

    assert response.status_code == 422
