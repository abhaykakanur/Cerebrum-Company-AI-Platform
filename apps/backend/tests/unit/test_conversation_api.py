"""HTTP-level proof that CIS Phase 4 Prompt 2's Conversation API routes
are wired correctly: create, list, get, rename, archive, delete,
export, search conversations/messages, send message, and stream message
(cerebrum.api.v1.conversations). Same ``app.dependency_overrides``
pattern established since test_ai_api.py.

Every route in this router that resolves ``SessionServiceDep``
(``create``/``send_message``/``stream_message``) transitively depends
on ``QdrantDep``/``Neo4jDep``/``OpenSearchDep``/``RedisDep`` — resolved
*eagerly* by FastAPI before the route body runs (see
cerebrum.dependencies.infrastructure's docstring: a disconnected
client's dependency getter raises immediately, not lazily on first
use), so ``get_session_service`` must be overridden for every request
in this file, not just the ones that would otherwise reach CIS Phase 4
Prompt 1's ``RAGService``. The ``_session_service`` autouse fixture
below installs one fake for the whole module: its ``create_session``
delegates to a real, SQLite-backed ``ConversationService`` (so
CRUD/list/search routes further down the same test still see genuinely
persisted data), while ``send_message``/``send_message_stream`` return
canned data, since those two are the ones that would otherwise need
live retrieval infrastructure.
"""

import json
import uuid
from collections.abc import AsyncIterator, Iterator

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
from cerebrum.application.conversation.conversation_service import ConversationService
from cerebrum.application.conversation.session_service import TurnResult
from cerebrum.application.retrieval.citation_service import EnrichedCitation
from cerebrum.config.security import SecuritySettings
from cerebrum.dependencies.conversation import get_session_service
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.conversation import Conversation
from cerebrum.infrastructure.database.models.message import Message
from cerebrum.infrastructure.security.password import PasswordHasher
from cerebrum.repositories.postgres.conversation_repository import (
    ConversationRepository,
)
from cerebrum.repositories.postgres.message_repository import MessageRepository
from cerebrum.utils.clock import utcnow

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
    for code in ["conversations:read", "conversations:write"]:
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
    citation = EnrichedCitation(
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
    return RAGAnswer(
        answer="Acme Corp makes widgets.",
        citations=[citation],
        confidence=ConfidenceBreakdown(
            retrieval_confidence=0.8,
            citation_coverage=1.0,
            context_completeness=0.5,
            source_diversity=1.0,
            overall=0.8,
        ),
        strategy="hybrid",
        provider="fake",
        model="fake-model",
        prompt_tokens=50,
        completion_tokens=10,
        context_truncated=False,
        all_retrieved_citations=[citation],
    )


class _FakeSessionService:
    """Stands in for the real ``SessionService`` — ``create_session``
    delegates to a real, SQLite-backed ``ConversationService`` (so
    every other route in this file, which reads through
    ``ConversationServiceDep`` against the same database, sees genuinely
    persisted data); ``send_message``/``send_message_stream`` return
    canned data, since those two are the ones that would otherwise
    reach CIS Phase 4 Prompt 1's ``RAGService`` and, through it,
    unreachable-in-this-sandbox retrieval infrastructure.
    """

    def __init__(
        self, conversation_service: ConversationService, session: AsyncSession
    ) -> None:
        self._conversations = conversation_service
        self._session = session
        self.last_send_call: dict = {}

    async def create_session(self, **kwargs):  # type: ignore[no-untyped-def]
        conversation = await self._conversations.create(**kwargs)
        await self._session.commit()
        return conversation

    async def send_message(  # type: ignore[no-untyped-def]
        self, conversation_id, *, workspace_id, user_id, question, provider, **kwargs
    ):
        self.last_send_call = {"conversation_id": conversation_id, "question": question}
        now = utcnow()
        conversation = Conversation(
            id=conversation_id,
            workspace_id=workspace_id,
            organization_id=uuid.uuid4(),
            user_id=user_id,
            title="Test",
            status="active",
            conversation_metadata={},
            created_at=now,
            updated_at=now,
        )
        user_message = Message(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            sequence_index=0,
            role="user",
            content=question,
            citations=[],
            context_references=[],
            prompt_tokens=0,
            completion_tokens=0,
            created_at=now,
        )
        assistant_message = Message(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            sequence_index=1,
            role="assistant",
            content=_answer().answer,
            citations=[],
            context_references=[],
            confidence=0.8,
            prompt_tokens=_answer().prompt_tokens,
            completion_tokens=_answer().completion_tokens,
            created_at=now,
        )
        return TurnResult(
            conversation=conversation,
            user_message=user_message,
            assistant_message=assistant_message,
            answer=_answer(),
        )

    async def send_message_stream(  # type: ignore[no-untyped-def]
        self,
        conversation_id,
        *,
        workspace_id,
        user_id,
        question,
        provider,
        cancellation=None,
        **kwargs,
    ) -> AsyncIterator:
        for event in (
            ProgressEvent(stage="retrieving"),
            TokenEvent(token="Acme Corp makes widgets."),
            CompletedEvent(answer=_answer()),
        ):
            yield event


@pytest.fixture(autouse=True)
def session_service_override(
    app: FastAPI, db_session: AsyncSession
) -> Iterator[_FakeSessionService]:
    conversation_service = ConversationService(
        conversation_repository=ConversationRepository(db_session),
        message_repository=MessageRepository(db_session),
        event_dispatcher=EventDispatcher(),
    )
    fake = _FakeSessionService(conversation_service, db_session)
    app.dependency_overrides[get_session_service] = lambda: fake
    yield fake
    del app.dependency_overrides[get_session_service]


async def test_create_conversation_endpoint(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(app, db_client, db_session, hasher)

    response = db_client.post(
        "/api/v1/conversations", json={"title": "Q1 Planning"}, headers=headers
    )

    assert response.status_code == 201, response.text
    body = response.json()["data"]
    assert body["title"] == "Q1 Planning"
    assert body["status"] == "active"


async def test_list_and_get_conversation(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(app, db_client, db_session, hasher)
    created = db_client.post(
        "/api/v1/conversations", json={"title": "First"}, headers=headers
    ).json()["data"]

    list_response = db_client.get("/api/v1/conversations", headers=headers)
    get_response = db_client.get(
        f"/api/v1/conversations/{created['id']}", headers=headers
    )

    assert list_response.status_code == 200
    assert len(list_response.json()["data"]) == 1
    assert get_response.status_code == 200
    detail = get_response.json()["data"]
    assert detail["id"] == created["id"]
    assert detail["messages"] == []


async def test_get_conversation_404_for_other_workspace(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(app, db_client, db_session, hasher)

    response = db_client.get(f"/api/v1/conversations/{uuid.uuid4()}", headers=headers)

    assert response.status_code == 404


async def test_rename_conversation(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(app, db_client, db_session, hasher)
    created = db_client.post(
        "/api/v1/conversations", json={"title": "Old"}, headers=headers
    ).json()["data"]

    response = db_client.patch(
        f"/api/v1/conversations/{created['id']}",
        json={"title": "New title"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["title"] == "New title"


async def test_archive_conversation(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(app, db_client, db_session, hasher)
    created = db_client.post("/api/v1/conversations", json={}, headers=headers).json()[
        "data"
    ]

    response = db_client.post(
        f"/api/v1/conversations/{created['id']}/archive", headers=headers
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "archived"


async def test_delete_conversation(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(app, db_client, db_session, hasher)
    created = db_client.post("/api/v1/conversations", json={}, headers=headers).json()[
        "data"
    ]

    delete_response = db_client.delete(
        f"/api/v1/conversations/{created['id']}", headers=headers
    )
    get_response = db_client.get(
        f"/api/v1/conversations/{created['id']}", headers=headers
    )

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


async def test_export_conversation(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(app, db_client, db_session, hasher)
    created = db_client.post(
        "/api/v1/conversations", json={"title": "Exported"}, headers=headers
    ).json()["data"]

    response = db_client.get(
        f"/api/v1/conversations/{created['id']}/export", headers=headers
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["conversation"]["title"] == "Exported"
    assert body["messages"] == []


async def test_search_conversations_endpoint(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(app, db_client, db_session, hasher)
    db_client.post(
        "/api/v1/conversations", json={"title": "Acme Contract Review"}, headers=headers
    )
    db_client.post(
        "/api/v1/conversations", json={"title": "Totally unrelated"}, headers=headers
    )

    response = db_client.get(
        "/api/v1/conversations/search", params={"q": "Acme"}, headers=headers
    )

    assert response.status_code == 200
    results = response.json()["data"]
    assert len(results) == 1
    assert results[0]["title"] == "Acme Contract Review"


async def test_search_messages_requires_q_or_reference_id(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(app, db_client, db_session, hasher)

    response = db_client.get("/api/v1/conversations/search/messages", headers=headers)

    assert response.status_code == 422


async def test_send_message_endpoint(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
    session_service_override: _FakeSessionService,
) -> None:
    headers = await _headers(app, db_client, db_session, hasher)
    created = db_client.post("/api/v1/conversations", json={}, headers=headers).json()[
        "data"
    ]

    response = db_client.post(
        f"/api/v1/conversations/{created['id']}/messages",
        json={"question": "What does Acme Corp make?"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["answer"]["answer"] == "Acme Corp makes widgets."
    assert body["user_message"]["content"] == "What does Acme Corp make?"
    assert body["assistant_message"]["role"] == "assistant"
    assert session_service_override.last_send_call["question"] == (
        "What does Acme Corp make?"
    )


async def test_stream_message_endpoint_emits_sse_events(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(app, db_client, db_session, hasher)
    created = db_client.post("/api/v1/conversations", json={}, headers=headers).json()[
        "data"
    ]

    with db_client.stream(
        "POST",
        f"/api/v1/conversations/{created['id']}/messages/stream",
        json={"question": "What does Acme Corp make?"},
        headers=headers,
    ) as response:
        assert response.status_code == 200
        events = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: ") :]))

    types = [e["type"] for e in events]
    assert types == ["progress", "token", "completed"]
    assert events[2]["answer"]["answer"] == "Acme Corp makes widgets."
