"""HTTP-level proof that CIS Phase 3 Prompt 2's Semantic Intelligence
routes are wired correctly: workspace-level search/hybrid/autocomplete/
statistics (cerebrum.api.v1.semantic), and the per-artifact similar/
reindex/regenerate-embeddings routes nested under documents/entities.
Same ``app.dependency_overrides`` pattern established since
test_extraction_api.py — real Qdrant/OpenSearch are unreachable in this
sandbox.
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
from cerebrum.dependencies.semantic import (
    get_embedding_service,
    get_hybrid_search_service,
    get_search_service,
    get_vector_index_service,
)
from cerebrum.infrastructure.security.password import PasswordHasher
from cerebrum.shared.errors.exceptions import NotFoundException

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
    for code in ["search:read", "documents:read", "documents:write", "entities:read"]:
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


def _search_hit():  # type: ignore[no-untyped-def]
    from cerebrum.application.semantic.hybrid_search_service import Citation, SearchHit

    return SearchHit(
        source_id="c1",
        kind="chunk",
        title="Report",
        snippet="...matching text...",
        fused_score=0.5,
        vector_score=0.4,
        keyword_score=3.0,
        citation=Citation(
            document_id=uuid.uuid4(),
            document_version_id=uuid.uuid4(),
            chunk_id=uuid.uuid4(),
            entity_id=None,
            confidence=0.4,
            provenance={"index": "qdrant"},
        ),
    )


class _FakeHybridSearchService:
    def __init__(self) -> None:
        self.last_call: dict = {}

    async def search(
        self,
        query_text,
        *,
        workspace_id,
        kinds=None,
        tags=None,
        limit=10,
        vector_weight=1.0,
        keyword_weight=1.0,
    ):
        self.last_call = {"query_text": query_text, "keyword_weight": keyword_weight}
        return [_search_hit()]

    async def similar_to_source(
        self, *, kind, source_id, workspace_id, kinds=None, limit=10
    ):
        return [_search_hit()]


class _NotFoundHybridSearchService:
    async def similar_to_source(
        self, *, kind, source_id, workspace_id, kinds=None, limit=10
    ):
        raise NotFoundException("No embedding found.")


class _FakeSearchService:
    async def autocomplete(self, *, prefix, workspace_id, limit=10):
        return [f"{prefix} suggestion"]

    async def get_statistics(self, *, workspace_id):
        return {"indexed_document_count": 7}

    async def index_version(self, **kwargs):
        return 5


class _FakeVectorIndexService:
    async def get_statistics(self, *, workspace_id):
        return {"vector_count": 12}


class _FakeEmbeddingService:
    def __init__(self) -> None:
        self.job = None

    async def embed_version(self, version_id, *, workspace_id, force=False):
        from cerebrum.infrastructure.database.models.processing_job import ProcessingJob

        self.job = ProcessingJob(
            id=uuid.uuid4(),
            document_version_id=version_id,
            job_type="embeddings",
            status="completed",
            progress_percent=100,
            retry_count=0,
            max_retries=3,
            error_message=None,
        )
        return self.job


async def test_semantic_search_endpoint(
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

    fake = _FakeHybridSearchService()
    app.dependency_overrides[get_hybrid_search_service] = lambda: fake
    try:
        response = db_client.get(
            "/api/v1/search/semantic?q=acme&limit=5", headers=headers
        )
    finally:
        del app.dependency_overrides[get_hybrid_search_service]

    assert response.status_code == 200, response.text
    assert fake.last_call["keyword_weight"] == 0.0
    body = response.json()["data"]
    assert body[0]["source_id"] == "c1"
    assert body[0]["citation"]["confidence"] == 0.4


async def test_hybrid_search_endpoint(
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

    fake = _FakeHybridSearchService()
    app.dependency_overrides[get_hybrid_search_service] = lambda: fake
    try:
        response = db_client.get("/api/v1/search/hybrid?q=acme", headers=headers)
    finally:
        del app.dependency_overrides[get_hybrid_search_service]

    assert response.status_code == 200, response.text
    assert len(response.json()["data"]) == 1


async def test_autocomplete_endpoint(
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

    app.dependency_overrides[get_search_service] = lambda: _FakeSearchService()
    try:
        response = db_client.get(
            "/api/v1/search/autocomplete?prefix=Rep", headers=headers
        )
    finally:
        del app.dependency_overrides[get_search_service]

    assert response.status_code == 200
    assert response.json()["data"]["suggestions"] == ["Rep suggestion"]


async def test_statistics_endpoint(
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

    app.dependency_overrides[get_vector_index_service] = (
        lambda: _FakeVectorIndexService()
    )
    app.dependency_overrides[get_search_service] = lambda: _FakeSearchService()
    try:
        response = db_client.get("/api/v1/search/statistics", headers=headers)
    finally:
        del app.dependency_overrides[get_vector_index_service]
        del app.dependency_overrides[get_search_service]

    assert response.status_code == 200
    assert response.json()["data"] == {"vector_count": 12, "indexed_document_count": 7}


async def test_similar_entities_endpoint(
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

    app.dependency_overrides[get_hybrid_search_service] = (
        lambda: _FakeHybridSearchService()
    )
    try:
        response = db_client.get(
            f"/api/v1/entities/{uuid.uuid4()}/similar", headers=headers
        )
    finally:
        del app.dependency_overrides[get_hybrid_search_service]

    assert response.status_code == 200
    assert len(response.json()["data"]) == 1


async def test_similar_entities_endpoint_returns_404_when_not_embedded(
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

    app.dependency_overrides[get_hybrid_search_service] = (
        lambda: _NotFoundHybridSearchService()
    )
    try:
        response = db_client.get(
            f"/api/v1/entities/{uuid.uuid4()}/similar", headers=headers
        )
    finally:
        del app.dependency_overrides[get_hybrid_search_service]

    assert response.status_code == 404


async def test_similar_documents_and_chunks_endpoints(
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

    app.dependency_overrides[get_hybrid_search_service] = (
        lambda: _FakeHybridSearchService()
    )
    try:
        doc_response = db_client.get(
            f"/api/v1/documents/{uuid.uuid4()}/versions/{uuid.uuid4()}/similar",
            headers=headers,
        )
        chunk_response = db_client.get(
            f"/api/v1/documents/{uuid.uuid4()}/versions/{uuid.uuid4()}/chunks/{uuid.uuid4()}/similar",
            headers=headers,
        )
    finally:
        del app.dependency_overrides[get_hybrid_search_service]

    assert doc_response.status_code == 200
    assert chunk_response.status_code == 200


async def test_regenerate_embeddings_endpoint(
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

    fake = _FakeEmbeddingService()
    app.dependency_overrides[get_embedding_service] = lambda: fake
    try:
        response = db_client.post(
            f"/api/v1/documents/{uuid.uuid4()}/versions/{uuid.uuid4()}/embeddings/regenerate",
            headers=headers,
        )
    finally:
        del app.dependency_overrides[get_embedding_service]

    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "completed"


async def test_reindex_endpoint(
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

    create_response = db_client.post(
        "/api/v1/documents", json={"name": "Report.pdf"}, headers=headers
    )
    document_id = create_response.json()["data"]["id"]
    version_response = db_client.post(
        f"/api/v1/documents/{document_id}/versions",
        json={
            "mime_type": "text/plain",
            "file_size_bytes": 10,
            "sha256_checksum": "a" * 64,
            "storage_path": "p",
            "original_filename": "Report.pdf",
            "uploaded_filename": "report.pdf",
            "uploaded_at": datetime.now(UTC).isoformat(),
        },
        headers=headers,
    )
    version_id = version_response.json()["data"]["id"]

    app.dependency_overrides[get_search_service] = lambda: _FakeSearchService()
    try:
        response = db_client.post(
            f"/api/v1/documents/{document_id}/versions/{version_id}/reindex",
            headers=headers,
        )
    finally:
        del app.dependency_overrides[get_search_service]

    assert response.status_code == 200, response.text
    assert response.json()["data"]["indexed_count"] == 5
