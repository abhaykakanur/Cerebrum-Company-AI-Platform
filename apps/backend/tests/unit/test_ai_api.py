"""HTTP-level proof that CIS Phase 4 Prompt 1's Enterprise RAG Engine
routes are wired correctly: ask, stream, citations, config, and
statistics (cerebrum.api.v1.ai). Same ``app.dependency_overrides``
pattern established since test_extraction_api.py / test_retrieval_api.py
— ``/ai/ask`` and ``/ai/ask/stream`` fake ``RAGService`` itself (the
pipeline underneath it is already proven in test_rag_service.py; this
file proves the HTTP wiring: routing, permission, request/response
schema, and SSE framing). ``/ai/config`` needs no override at all — it
only reads ``Settings.ai``, already a real, fully-defaulted object.
"""

import json
import uuid
from collections.abc import AsyncIterator

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

from cerebrum.application.ai.ai_response_service import ConfidenceBreakdown, RAGAnswer
from cerebrum.application.ai.rag_service import (
    CompletedEvent,
    ProgressEvent,
    TokenEvent,
)
from cerebrum.application.retrieval.citation_service import EnrichedCitation
from cerebrum.application.retrieval.retrieval_service import (
    RetrievalResult,
    RetrievalStrategy,
)
from cerebrum.application.semantic.hybrid_search_service import Citation, SearchHit
from cerebrum.config.security import SecuritySettings
from cerebrum.dependencies.ai import get_ai_usage_stats_service, get_rag_service
from cerebrum.dependencies.retrieval import (
    get_citation_service,
    get_retrieval_service,
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
    for code in ["ai:ask", "ai:read"]:
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


def _answer() -> RAGAnswer:
    return RAGAnswer(
        answer="Acme Corp makes widgets. [1]",
        citations=[
            EnrichedCitation(
                document_id=uuid.uuid4(),
                document_version_id=uuid.uuid4(),
                chunk_id=uuid.uuid4(),
                entity_id=None,
                confidence=0.9,
                provenance={},
                document_name="Report.pdf",
                version_number=1,
                chunk_index=0,
                entity_name=None,
            )
        ],
        confidence=ConfidenceBreakdown(
            retrieval_confidence=0.8,
            citation_coverage=1.0,
            context_completeness=0.5,
            source_diversity=1.0,
            overall=0.825,
        ),
        strategy="hybrid",
        provider="local",
        model="local-extractive-v1",
        prompt_tokens=100,
        completion_tokens=20,
        context_truncated=False,
    )


class _FakeRAGService:
    def __init__(self, answer: RAGAnswer | None = None, stream_events=None) -> None:
        self.answer = answer or _answer()
        self.stream_events = stream_events
        self.last_ask_call: dict = {}

    async def ask(self, question, *, workspace_id, provider, **kwargs):  # type: ignore[no-untyped-def]
        self.last_ask_call = {
            "question": question,
            "workspace_id": workspace_id,
            **kwargs,
        }
        return self.answer

    async def ask_stream(  # type: ignore[no-untyped-def]
        self, question, *, workspace_id, provider, cancellation=None, **kwargs
    ) -> AsyncIterator:
        events = self.stream_events or [
            ProgressEvent(stage="retrieving"),
            TokenEvent(token="Hello"),
            CompletedEvent(answer=self.answer),
        ]
        for event in events:
            yield event


class _FakeRetrievalService:
    async def retrieve(  # type: ignore[no-untyped-def]
        self, question, *, workspace_id, strategy=RetrievalStrategy.HYBRID, **kwargs
    ):
        hit = SearchHit(
            source_id="c1",
            kind="chunk",
            title="Report",
            snippet="...",
            fused_score=0.5,
            vector_score=0.5,
            keyword_score=None,
            citation=Citation(
                document_id=uuid.uuid4(),
                document_version_id=uuid.uuid4(),
                chunk_id=uuid.uuid4(),
                entity_id=None,
                confidence=0.9,
                provenance={},
            ),
        )
        return RetrievalResult(hits=[hit], strategy=strategy, query_text=question)


class _FakeCitationService:
    async def build_citations(self, hits, *, workspace_id):  # type: ignore[no-untyped-def]
        return [
            EnrichedCitation(
                document_id=uuid.uuid4(),
                document_version_id=None,
                chunk_id=None,
                entity_id=None,
                confidence=0.9,
                provenance={},
                document_name="Report.pdf",
                version_number=None,
                chunk_index=None,
                entity_name=None,
            )
        ]


class _FakeUsageStatsService:
    async def get_statistics(self, *, workspace_id):  # type: ignore[no-untyped-def]
        return {
            "question_count": 3,
            "prompt_tokens": 300,
            "completion_tokens": 60,
            "providers": {"local": 3},
        }


async def test_ask_endpoint(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(app, db_client, db_session, hasher)
    fake = _FakeRAGService()
    app.dependency_overrides[get_rag_service] = lambda: fake
    try:
        response = db_client.post(
            "/api/v1/ai/ask",
            json={"question": "What does Acme Corp make?"},
            headers=headers,
        )
    finally:
        del app.dependency_overrides[get_rag_service]

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["answer"] == "Acme Corp makes widgets. [1]"
    assert body["citations"][0]["document_name"] == "Report.pdf"
    assert body["confidence"]["overall"] == pytest.approx(0.825)
    assert fake.last_ask_call["question"] == "What does Acme Corp make?"


async def test_ask_endpoint_rejects_empty_question(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(app, db_client, db_session, hasher)
    app.dependency_overrides[get_rag_service] = lambda: _FakeRAGService()
    try:
        response = db_client.post(
            "/api/v1/ai/ask", json={"question": ""}, headers=headers
        )
    finally:
        del app.dependency_overrides[get_rag_service]

    assert response.status_code == 422


async def test_stream_answer_endpoint_emits_sse_events(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(app, db_client, db_session, hasher)
    fake = _FakeRAGService()
    app.dependency_overrides[get_rag_service] = lambda: fake
    try:
        with db_client.stream(
            "POST",
            "/api/v1/ai/ask/stream",
            json={"question": "What does Acme Corp make?"},
            headers=headers,
        ) as response:
            assert response.status_code == 200
            events = []
            for line in response.iter_lines():
                if line.startswith("data: "):
                    events.append(json.loads(line[len("data: ") :]))
    finally:
        del app.dependency_overrides[get_rag_service]

    types = [e["type"] for e in events]
    assert types == ["progress", "token", "completed"]
    assert events[1]["token"] == "Hello"
    assert events[2]["answer"]["answer"] == "Acme Corp makes widgets. [1]"


async def test_citations_endpoint(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(app, db_client, db_session, hasher)
    app.dependency_overrides[get_retrieval_service] = lambda: _FakeRetrievalService()
    app.dependency_overrides[get_citation_service] = lambda: _FakeCitationService()
    try:
        response = db_client.post(
            "/api/v1/ai/citations",
            json={"question": "What does Acme Corp make?"},
            headers=headers,
        )
    finally:
        del app.dependency_overrides[get_retrieval_service]
        del app.dependency_overrides[get_citation_service]

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert len(body) == 1
    assert body[0]["document_name"] == "Report.pdf"


async def test_config_endpoint_needs_no_override(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(app, db_client, db_session, hasher)

    response = db_client.get("/api/v1/ai/config", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["default_provider"] == "local"
    assert "local" in body["available_providers"]
    assert "ollama" in body["available_providers"]
    assert "openai" not in body["available_providers"]
    assert body["default_model_by_provider"]["local"] == "local-extractive-v1"


async def test_statistics_endpoint(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(app, db_client, db_session, hasher)
    app.dependency_overrides[get_ai_usage_stats_service] = (
        lambda: _FakeUsageStatsService()
    )
    try:
        response = db_client.get("/api/v1/ai/statistics", headers=headers)
    finally:
        del app.dependency_overrides[get_ai_usage_stats_service]

    assert response.status_code == 200, response.text
    assert response.json()["data"] == {
        "question_count": 3,
        "prompt_tokens": 300,
        "completion_tokens": 60,
        "providers": {"local": 3},
    }
