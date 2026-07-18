"""HTTP-level proof that CIS Phase 2 Prompt 4's Knowledge Preparation
routes (reprocess/manifest/chunks/progress/cancel-processing) are wired
correctly — same ``app.dependency_overrides`` pattern
test_extraction_api.py/test_upload_api.py established.
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
from cerebrum.dependencies.knowledge import (
    get_chunking_service,
    get_knowledge_preparation_service,
)
from cerebrum.infrastructure.database.models.chunk import Chunk, ChunkingStrategy
from cerebrum.infrastructure.database.models.document_manifest import (
    DocumentManifest,
    ManifestStatus,
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


class _FakeKnowledgePreparationService:
    def __init__(self) -> None:
        self.manifest = DocumentManifest(
            id=uuid.uuid4(),
            document_version_id=uuid.uuid4(),
            extraction_id=uuid.uuid4(),
            status=ManifestStatus.READY.value,
            chunking_strategy=ChunkingStrategy.RECURSIVE.value,
            chunk_count=3,
            total_character_count=300,
            statistics={"avg_chunk_size": 100},
            error_message=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    async def prepare(self, version_id, *, workspace_id, strategy, force):  # type: ignore[no-untyped-def]
        return self.manifest

    async def get_manifest(self, version_id, *, workspace_id):  # type: ignore[no-untyped-def]
        return self.manifest

    async def get_progress(self, version_id, *, workspace_id):  # type: ignore[no-untyped-def]
        from cerebrum.application.knowledge.knowledge_preparation_service import (
            PipelineProgress,
        )

        return PipelineProgress(
            extraction_status="completed",
            extraction_progress_percent=100,
            chunking_status="completed",
            chunking_progress_percent=100,
            overall_progress_percent=100,
        )

    async def cancel(self, version_id, *, workspace_id):  # type: ignore[no-untyped-def]
        return 2


class _FakeChunkingService:
    async def list_chunks(self, version_id, *, workspace_id):  # type: ignore[no-untyped-def]
        return [
            Chunk(
                id=uuid.uuid4(),
                document_version_id=version_id,
                extraction_id=uuid.uuid4(),
                parent_chunk_id=None,
                strategy=ChunkingStrategy.RECURSIVE.value,
                chunk_index=0,
                text="hello",
                character_count=5,
                start_offset=0,
                end_offset=5,
                overlap_with_previous=0,
                chunk_metadata={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        ]


async def test_reprocess_endpoint_returns_the_manifest(
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

    fake_service = _FakeKnowledgePreparationService()
    app.dependency_overrides[get_knowledge_preparation_service] = lambda: fake_service
    try:
        response = db_client.post(
            f"/api/v1/documents/{uuid.uuid4()}/versions/{uuid.uuid4()}/reprocess",
            json={"strategy": "recursive", "force": False},
            headers=headers,
        )
    finally:
        del app.dependency_overrides[get_knowledge_preparation_service]

    assert response.status_code == 201, response.text
    body = response.json()["data"]
    assert body["status"] == "ready"
    assert body["chunk_count"] == 3


async def test_manifest_endpoint_returns_the_manifest(
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

    app.dependency_overrides[get_knowledge_preparation_service] = (
        lambda: _FakeKnowledgePreparationService()
    )
    try:
        response = db_client.get(
            f"/api/v1/documents/{uuid.uuid4()}/versions/{uuid.uuid4()}/manifest",
            headers=headers,
        )
    finally:
        del app.dependency_overrides[get_knowledge_preparation_service]

    assert response.status_code == 200
    assert response.json()["data"]["chunking_strategy"] == "recursive"


async def test_chunks_endpoint_lists_chunks(
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

    app.dependency_overrides[get_chunking_service] = lambda: _FakeChunkingService()
    try:
        response = db_client.get(
            f"/api/v1/documents/{uuid.uuid4()}/versions/{uuid.uuid4()}/chunks",
            headers=headers,
        )
    finally:
        del app.dependency_overrides[get_chunking_service]

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["text"] == "hello"


async def test_progress_endpoint_returns_aggregate_progress(
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

    app.dependency_overrides[get_knowledge_preparation_service] = (
        lambda: _FakeKnowledgePreparationService()
    )
    try:
        response = db_client.get(
            f"/api/v1/documents/{uuid.uuid4()}/versions/{uuid.uuid4()}/progress",
            headers=headers,
        )
    finally:
        del app.dependency_overrides[get_knowledge_preparation_service]

    assert response.status_code == 200
    assert response.json()["data"]["overall_progress_percent"] == 100


async def test_cancel_processing_endpoint_returns_cancelled_count(
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

    app.dependency_overrides[get_knowledge_preparation_service] = (
        lambda: _FakeKnowledgePreparationService()
    )
    try:
        response = db_client.post(
            f"/api/v1/documents/{uuid.uuid4()}/versions/{uuid.uuid4()}/cancel-processing",
            headers=headers,
        )
    finally:
        del app.dependency_overrides[get_knowledge_preparation_service]

    assert response.status_code == 200
    assert response.json()["data"]["cancelled_job_count"] == 2
