"""HTTP-level proof that CIS Phase 3 Prompt 3's Retrieval Engine routes
are wired correctly: retrieve, context, explain, similar-entities,
similar-documents, graph-context, and statistics
(cerebrum.api.v1.retrieval). Same ``app.dependency_overrides`` pattern
established since test_extraction_api.py / test_semantic_api.py — real
Qdrant/OpenSearch/Neo4j/Postgres collaborators are unreachable in this
sandbox, so every retrieval-layer service is faked at its DI provider.
"""

import uuid

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

from cerebrum.application.retrieval.citation_service import EnrichedCitation
from cerebrum.application.retrieval.context_builder_service import ContextPackage
from cerebrum.application.retrieval.explainability_service import Explanation
from cerebrum.application.retrieval.ranking_service import RankedResult, RankingFactors
from cerebrum.application.retrieval.retrieval_service import (
    RetrievalResult,
    RetrievalStrategy,
)
from cerebrum.application.semantic.hybrid_search_service import Citation, SearchHit
from cerebrum.config.security import SecuritySettings
from cerebrum.dependencies.knowledge_graph import get_knowledge_graph_service
from cerebrum.dependencies.retrieval import (
    get_citation_service,
    get_context_builder_service,
    get_explainability_service,
    get_ranking_service,
    get_retrieval_service,
)
from cerebrum.dependencies.semantic import (
    get_hybrid_search_service,
    get_search_service,
    get_vector_index_service,
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
    for code in ["search:read"]:
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


def _hit(source_id: str = "c1") -> SearchHit:
    return SearchHit(
        source_id=source_id,
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


class _FakeRetrievalService:
    def __init__(self, hits: list[SearchHit] | None = None) -> None:
        self.hits = hits if hits is not None else [_hit()]
        self.last_call: dict = {}

    async def retrieve(
        self,
        query_text: str | None = None,
        *,
        workspace_id,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        **kwargs,
    ) -> RetrievalResult:
        self.last_call = {"query_text": query_text, "strategy": strategy, **kwargs}
        return RetrievalResult(
            hits=self.hits,
            strategy=strategy,
            query_text=query_text,
            seed_entity_id=kwargs.get("entity_id"),
        )


class _FakeRankingService:
    def rank(self, hits: list[SearchHit], **kwargs) -> list[RankedResult]:
        return [
            RankedResult(
                hit=hit,
                factors=RankingFactors(
                    hybrid_score=0.5,
                    vector_similarity=0.5,
                    bm25_score=0.5,
                    graph_proximity=0.0,
                    entity_importance=0.0,
                    recency=0.5,
                    source_confidence=hit.citation.confidence,
                    document_quality=0.5,
                ),
                final_score=0.9,
            )
            for hit in hits
        ]


class _FakeContextBuilderService:
    async def build(
        self, hits: list[SearchHit], *, workspace_id, **kwargs
    ) -> ContextPackage:
        return ContextPackage(
            query_text=kwargs.get("query_text"),
            documents=[],
            chunks=[],
            entities=[],
            entities_by_type={},
            relationships=[],
            graph_neighbors={},
            version_history=[],
            citations=[],
            truncated=False,
        )


class _FakeCitationService:
    async def build_citations(
        self, hits: list[SearchHit], *, workspace_id
    ) -> list[EnrichedCitation]:
        return [
            EnrichedCitation(
                document_id=None,
                document_version_id=None,
                chunk_id=None,
                entity_id=None,
                confidence=1.0,
                provenance={},
                document_name=None,
                version_number=None,
                chunk_index=None,
                entity_name=None,
            )
        ]


class _FakeExplainabilityService:
    def explain_batch(
        self, ranked_results: list[RankedResult], *, strategy: str
    ) -> list[Explanation]:
        return [
            Explanation(
                source_id=result.hit.source_id,
                strategy=strategy,
                why_selected="Strongest signal was hybrid_score.",
                ranking_factors=result.factors,
                supporting_evidence=[],
                confidence_breakdown=result.factors.as_dict(),
                final_score=result.final_score,
            )
            for result in ranked_results
        ]


class _FakeHybridSearchService:
    async def similar_to_source(self, *, kind, source_id, workspace_id, **kwargs):
        return [_hit()]


class _FakeVectorIndexService:
    async def get_statistics(self, *, workspace_id):
        return {"vector_count": 12}


class _FakeSearchService:
    async def get_statistics(self, *, workspace_id):
        return {"indexed_document_count": 7}


class _FakeKnowledgeGraphService:
    async def get_statistics(self, *, workspace_id):
        return {"entity_count": 4, "relationship_count": 2}


async def _headers(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> dict[str, str]:
    workspace_id, user = await _seed_full_access_tenant(db_session, hasher)
    return _login(
        db_client,
        email=user.email,
        password="CorrectHorse123!",
        workspace_id=workspace_id,
    )


async def test_retrieve_endpoint(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(app, db_client, db_session, hasher)
    fake_retrieval = _FakeRetrievalService()
    app.dependency_overrides[get_retrieval_service] = lambda: fake_retrieval
    app.dependency_overrides[get_ranking_service] = lambda: _FakeRankingService()
    try:
        response = db_client.get(
            "/api/v1/retrieval/retrieve?q=acme&strategy=hybrid", headers=headers
        )
    finally:
        del app.dependency_overrides[get_retrieval_service]
        del app.dependency_overrides[get_ranking_service]

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert len(body) == 1
    assert body[0]["hit"]["source_id"] == "c1"
    assert body[0]["final_score"] == 0.9
    assert fake_retrieval.last_call["strategy"] is RetrievalStrategy.HYBRID


async def test_context_endpoint(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(app, db_client, db_session, hasher)
    app.dependency_overrides[get_retrieval_service] = lambda: _FakeRetrievalService()
    app.dependency_overrides[get_context_builder_service] = (
        lambda: _FakeContextBuilderService()
    )
    app.dependency_overrides[get_citation_service] = lambda: _FakeCitationService()
    try:
        response = db_client.get("/api/v1/retrieval/context?q=acme", headers=headers)
    finally:
        del app.dependency_overrides[get_retrieval_service]
        del app.dependency_overrides[get_context_builder_service]
        del app.dependency_overrides[get_citation_service]

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["truncated"] is False
    assert len(body["citations"]) == 1


async def test_explain_endpoint(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(app, db_client, db_session, hasher)
    app.dependency_overrides[get_retrieval_service] = lambda: _FakeRetrievalService()
    app.dependency_overrides[get_ranking_service] = lambda: _FakeRankingService()
    app.dependency_overrides[get_explainability_service] = (
        lambda: _FakeExplainabilityService()
    )
    try:
        response = db_client.get("/api/v1/retrieval/explain?q=acme", headers=headers)
    finally:
        del app.dependency_overrides[get_retrieval_service]
        del app.dependency_overrides[get_ranking_service]
        del app.dependency_overrides[get_explainability_service]

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert len(body) == 1
    assert body[0]["source_id"] == "c1"
    assert "why_selected" in body[0]


async def test_similar_entities_endpoint(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(app, db_client, db_session, hasher)
    app.dependency_overrides[get_retrieval_service] = lambda: _FakeRetrievalService()
    app.dependency_overrides[get_ranking_service] = lambda: _FakeRankingService()
    try:
        response = db_client.get(
            f"/api/v1/retrieval/similar-entities/{uuid.uuid4()}", headers=headers
        )
    finally:
        del app.dependency_overrides[get_retrieval_service]
        del app.dependency_overrides[get_ranking_service]

    assert response.status_code == 200, response.text
    assert len(response.json()["data"]) == 1


async def test_similar_documents_endpoint(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(app, db_client, db_session, hasher)
    app.dependency_overrides[get_hybrid_search_service] = (
        lambda: _FakeHybridSearchService()
    )
    app.dependency_overrides[get_ranking_service] = lambda: _FakeRankingService()
    try:
        response = db_client.get(
            f"/api/v1/retrieval/similar-documents/{uuid.uuid4()}", headers=headers
        )
    finally:
        del app.dependency_overrides[get_hybrid_search_service]
        del app.dependency_overrides[get_ranking_service]

    assert response.status_code == 200, response.text
    assert len(response.json()["data"]) == 1


async def test_graph_context_endpoint(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(app, db_client, db_session, hasher)
    app.dependency_overrides[get_retrieval_service] = lambda: _FakeRetrievalService()
    app.dependency_overrides[get_context_builder_service] = (
        lambda: _FakeContextBuilderService()
    )
    app.dependency_overrides[get_citation_service] = lambda: _FakeCitationService()
    try:
        response = db_client.get(
            f"/api/v1/retrieval/graph-context/{uuid.uuid4()}", headers=headers
        )
    finally:
        del app.dependency_overrides[get_retrieval_service]
        del app.dependency_overrides[get_context_builder_service]
        del app.dependency_overrides[get_citation_service]

    assert response.status_code == 200, response.text


async def test_statistics_endpoint(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(app, db_client, db_session, hasher)
    app.dependency_overrides[get_vector_index_service] = (
        lambda: _FakeVectorIndexService()
    )
    app.dependency_overrides[get_search_service] = lambda: _FakeSearchService()
    app.dependency_overrides[get_knowledge_graph_service] = (
        lambda: _FakeKnowledgeGraphService()
    )
    try:
        response = db_client.get("/api/v1/retrieval/statistics", headers=headers)
    finally:
        del app.dependency_overrides[get_vector_index_service]
        del app.dependency_overrides[get_search_service]
        del app.dependency_overrides[get_knowledge_graph_service]

    assert response.status_code == 200, response.text
    assert response.json()["data"] == {
        "vector_count": 12,
        "indexed_document_count": 7,
        "entity_count": 4,
        "relationship_count": 2,
    }
