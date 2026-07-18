"""HTTP-level proof that CIS Phase 2 Prompt 2's upload/processing routes
are wired correctly (multipart parsing, RBAC, response envelope) — the
same real-middleware-pipeline style as test_auth_api.py/
test_knowledge_api.py.

``UploadServiceDep``/``ProcessingServiceDep`` are overridden with fakes
via ``app.dependency_overrides`` (the exact mechanism
apps/backend/tests/conftest.py's ``db_client`` fixture already uses for
``get_db_session``): real MinIO/Redis are unreachable in this unit-test
environment, and unlike PostgreSQL (stood in for by SQLite), there is no
in-memory substitute this suite already relies on for either — the fake
services below exercise everything *except* the concrete
MinIO/Redis adapters, which cerebrum.infrastructure.storage.minio_files/
cerebrum.infrastructure.queue.redis_queue's own docstrings note as
untested-in-this-sandbox for the same reason.
``bulk-delete`` needs neither and is tested directly, no override.
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
from cerebrum.dependencies.knowledge import get_processing_service, get_upload_service
from cerebrum.infrastructure.database.models.document_version import (
    DocumentVersion,
    UploadStatus,
    VersionType,
)
from cerebrum.infrastructure.database.models.processing_job import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
)
from cerebrum.infrastructure.security.password import PasswordHasher

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
    for code in ["documents:read", "documents:write", "documents:delete"]:
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


class _FakeUploadService:
    async def upload_new_version(self, document_id, **kwargs):  # type: ignore[no-untyped-def]
        return DocumentVersion(
            id=uuid.uuid4(),
            document_id=document_id,
            version_number=1,
            version_type=VersionType.MINOR.value,
            is_current=True,
            upload_status=UploadStatus.STORED.value,
            change_summary=None,
            created_at=datetime.now(UTC),
            created_by=None,
        )


class _FakeProcessingService:
    def __init__(self) -> None:
        self.job = ProcessingJob(
            id=uuid.uuid4(),
            document_version_id=uuid.uuid4(),
            job_type=ProcessingJobType.PARSING.value,
            status=ProcessingJobStatus.PENDING.value,
            progress_percent=0,
            retry_count=0,
            max_retries=3,
            error_message=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    async def get(self, job_id, *, workspace_id):  # type: ignore[no-untyped-def]
        return self.job

    async def retry(self, job_id, *, workspace_id):  # type: ignore[no-untyped-def]
        self.job.status = ProcessingJobStatus.PENDING.value
        self.job.retry_count += 1
        return self.job

    async def cancel(self, job_id, *, workspace_id):  # type: ignore[no-untyped-def]
        self.job.status = ProcessingJobStatus.CANCELLED.value
        return self.job


async def test_upload_endpoint_returns_the_created_version(
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

    doc_resp = db_client.post(
        "/api/v1/documents", json={"name": "Report.pdf"}, headers=headers
    )
    document_id = doc_resp.json()["data"]["id"]

    app.dependency_overrides[get_upload_service] = lambda: _FakeUploadService()
    try:
        response = db_client.post(
            f"/api/v1/documents/{document_id}/upload",
            files={"file": ("report.pdf", b"%PDF-1.4 content", "application/pdf")},
            headers=headers,
        )
    finally:
        del app.dependency_overrides[get_upload_service]

    assert response.status_code == 201, response.text
    body = response.json()["data"]
    assert body["upload_status"] == "stored"
    assert body["is_current"] is True


async def test_bulk_delete_reports_requested_and_succeeded_counts(
    db_client: TestClient, db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    workspace_id, user = await _seed_full_access_tenant(db_session, hasher)
    headers = _login(
        db_client,
        email=user.email,
        password="CorrectHorse123!",
        workspace_id=workspace_id,
    )

    doc_a = db_client.post(
        "/api/v1/documents", json={"name": "A.pdf"}, headers=headers
    ).json()["data"]
    doc_b = db_client.post(
        "/api/v1/documents", json={"name": "B.pdf"}, headers=headers
    ).json()["data"]

    response = db_client.post(
        "/api/v1/documents/bulk-delete",
        json={"document_ids": [doc_a["id"], doc_b["id"], str(uuid.uuid4())]},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"] == {"requested": 3, "succeeded": 2}

    after = db_client.get(f"/api/v1/documents/{doc_a['id']}", headers=headers)
    assert after.status_code == 404


async def test_processing_job_status_retry_cancel_over_http(
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

    fake_processing = _FakeProcessingService()
    app.dependency_overrides[get_processing_service] = lambda: fake_processing
    try:
        status_resp = db_client.get(
            f"/api/v1/processing-jobs/{fake_processing.job.id}", headers=headers
        )
        assert status_resp.status_code == 200
        assert status_resp.json()["data"]["status"] == "pending"

        cancel_resp = db_client.post(
            f"/api/v1/processing-jobs/{fake_processing.job.id}/cancel", headers=headers
        )
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["data"]["status"] == "cancelled"

        retry_resp = db_client.post(
            f"/api/v1/processing-jobs/{fake_processing.job.id}/retry", headers=headers
        )
        assert retry_resp.status_code == 200
        assert retry_resp.json()["data"]["status"] == "pending"
        assert retry_resp.json()["data"]["retry_count"] == 1
    finally:
        del app.dependency_overrides[get_processing_service]
