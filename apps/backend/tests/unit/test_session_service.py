"""Proves CIS Phase 4 Prompt 2's ``SessionService``: a full turn
(persist user message -> invoke ``RAGService`` with memory as
conversation history -> persist assistant message with citations/
context references -> trigger summarization), streaming persistence
(user message written before generation, assistant message only once
the stream actually completes — never on cancellation/error), and
:meth:`resume`.

``RAGService`` itself is faked at its own service-level interface
(already proven end-to-end in test_rag_service.py) — this file's
subject is ``SessionService``'s orchestration and persistence, the same
"fake the collaborator service, not its internals" boundary
test_rag_service.py's own docstring explains for ``RetrievalService``/
``ContextBuilderService``/``CitationService``.
"""

import uuid
from collections.abc import AsyncIterator

import pytest
from _auth_factories import create_organization, create_user, create_workspace
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.ai.ai_response_service import ConfidenceBreakdown, RAGAnswer
from cerebrum.application.ai.rag_service import (
    CompletedEvent,
    ErrorEvent,
    ProgressEvent,
    StreamEvent,
    TokenEvent,
)
from cerebrum.application.conversation.conversation_service import ConversationService
from cerebrum.application.conversation.conversation_summary_service import (
    ConversationSummaryService,
)
from cerebrum.application.conversation.memory_service import MemoryService
from cerebrum.application.conversation.session_service import SessionService
from cerebrum.application.retrieval.citation_service import EnrichedCitation
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.message import MessageRole
from cerebrum.repositories.postgres.conversation_repository import (
    ConversationRepository,
)
from cerebrum.repositories.postgres.message_repository import MessageRepository

pytestmark = pytest.mark.unit


def _hasher():  # type: ignore[no-untyped-def]
    from cerebrum.config.security import SecuritySettings
    from cerebrum.infrastructure.security.password import PasswordHasher

    return PasswordHasher(SecuritySettings())


async def _tenant(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    unique = uuid.uuid4().hex[:8]
    org = await create_organization(session, slug=f"acme-{unique}")
    workspace = await create_workspace(session, organization_id=org.id)
    user = await create_user(
        session,
        organization_id=org.id,
        email=f"alice-{unique}@acme.example",
        password="CorrectHorse123!",
        hasher=_hasher(),
    )
    await session.commit()
    return org.id, workspace.id, user.id


def _answer(*, citations: list[EnrichedCitation] | None = None) -> RAGAnswer:
    resolved = citations or [
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
    return RAGAnswer(
        answer="Acme Corp makes widgets.",
        citations=resolved,
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
        all_retrieved_citations=resolved,
    )


class _FakeRAGService:
    def __init__(
        self,
        *,
        answer: RAGAnswer | None = None,
        stream_events: list[StreamEvent] | None = None,
    ) -> None:
        self.answer = answer or _answer()
        self.stream_events = stream_events
        self.ask_calls: list[dict] = []
        self.ask_stream_calls: list[dict] = []

    async def ask(self, question, *, workspace_id, provider, **kwargs) -> RAGAnswer:  # type: ignore[no-untyped-def]
        self.ask_calls.append({"question": question, **kwargs})
        return self.answer

    async def ask_stream(  # type: ignore[no-untyped-def]
        self, question, *, workspace_id, provider, cancellation=None, **kwargs
    ) -> AsyncIterator[StreamEvent]:
        self.ask_stream_calls.append({"question": question, **kwargs})
        events = self.stream_events or [
            ProgressEvent(stage="retrieving"),
            TokenEvent(token="Acme Corp makes widgets."),
            CompletedEvent(answer=self.answer),
        ]
        for event in events:
            yield event


class _FakeProvider:
    name = "fake"
    default_model = "fake-model"


def _session_service(
    db_session: AsyncSession,
    *,
    rag: _FakeRAGService,
    events: EventDispatcher | None = None,
) -> SessionService:
    dispatcher = events or EventDispatcher()
    return SessionService(
        conversation_service=ConversationService(
            conversation_repository=ConversationRepository(db_session),
            message_repository=MessageRepository(db_session),
            event_dispatcher=dispatcher,
        ),
        memory_service=MemoryService(
            conversation_repository=ConversationRepository(db_session),
            message_repository=MessageRepository(db_session),
        ),
        summary_service=ConversationSummaryService(
            conversation_repository=ConversationRepository(db_session),
            message_repository=MessageRepository(db_session),
            event_dispatcher=dispatcher,
        ),
        rag_service=rag,  # type: ignore[arg-type]
    )


async def test_create_session_delegates_to_conversation_service(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _session_service(db_session, rag=_FakeRAGService())

    conversation = await service.create_session(
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        title="New chat",
    )
    await db_session.commit()

    assert conversation.title == "New chat"
    assert conversation.user_id == user_id


async def test_send_message_persists_user_and_assistant_messages(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    rag = _FakeRAGService()
    service = _session_service(db_session, rag=rag)
    conversation = await service.create_session(
        workspace_id=workspace_id, organization_id=organization_id, user_id=user_id
    )
    await db_session.commit()

    turn = await service.send_message(
        conversation.id,
        workspace_id=workspace_id,
        user_id=user_id,
        question="What does Acme Corp make?",
        provider=_FakeProvider(),  # type: ignore[arg-type]
    )
    await db_session.commit()

    assert turn.user_message.role == MessageRole.USER.value
    assert turn.user_message.content == "What does Acme Corp make?"
    assert turn.assistant_message.role == MessageRole.ASSISTANT.value
    assert turn.assistant_message.content == "Acme Corp makes widgets."
    assert turn.assistant_message.sequence_index == 1
    assert turn.answer is rag.answer


async def test_send_message_passes_memory_as_conversation_history(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    rag = _FakeRAGService()
    service = _session_service(db_session, rag=rag)
    conversation = await service.create_session(
        workspace_id=workspace_id, organization_id=organization_id, user_id=user_id
    )
    await db_session.commit()

    await service.send_message(
        conversation.id,
        workspace_id=workspace_id,
        user_id=user_id,
        question="First question",
        provider=_FakeProvider(),  # type: ignore[arg-type]
    )
    await db_session.commit()
    await service.send_message(
        conversation.id,
        workspace_id=workspace_id,
        user_id=user_id,
        question="Second question",
        provider=_FakeProvider(),  # type: ignore[arg-type]
    )
    await db_session.commit()

    second_call_history = rag.ask_calls[1]["conversation_history"]
    contents = [m.content for m in second_call_history]
    assert "First question" in contents
    assert "Acme Corp makes widgets." in contents


async def test_send_message_persists_citations_and_context_references(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _session_service(db_session, rag=_FakeRAGService())
    conversation = await service.create_session(
        workspace_id=workspace_id, organization_id=organization_id, user_id=user_id
    )
    await db_session.commit()

    turn = await service.send_message(
        conversation.id,
        workspace_id=workspace_id,
        user_id=user_id,
        question="q",
        provider=_FakeProvider(),  # type: ignore[arg-type]
    )
    await db_session.commit()

    assert len(turn.assistant_message.citations) == 1
    assert turn.assistant_message.citations[0]["document_name"] == "Report.pdf"
    assert len(turn.assistant_message.context_references) == 1
    assert turn.assistant_message.confidence == pytest.approx(0.8)


async def test_send_message_stream_persists_user_message_before_completion(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    events = [ProgressEvent(stage="retrieving"), TokenEvent(token="partial")]
    rag = _FakeRAGService(stream_events=events)
    service = _session_service(db_session, rag=rag)
    conversation = await service.create_session(
        workspace_id=workspace_id, organization_id=organization_id, user_id=user_id
    )
    await db_session.commit()

    collected = [
        event
        async for event in service.send_message_stream(
            conversation.id,
            workspace_id=workspace_id,
            user_id=user_id,
            question="q",
            provider=_FakeProvider(),  # type: ignore[arg-type]
        )
    ]
    await db_session.commit()

    assert not any(isinstance(e, CompletedEvent) for e in collected)
    history = await service._conversations.get_history(  # noqa: SLF001
        conversation.id, workspace_id=workspace_id, user_id=user_id
    )
    assert [m.role for m in history] == [MessageRole.USER.value]


async def test_send_message_stream_persists_assistant_message_on_completion(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    rag = _FakeRAGService()
    service = _session_service(db_session, rag=rag)
    conversation = await service.create_session(
        workspace_id=workspace_id, organization_id=organization_id, user_id=user_id
    )
    await db_session.commit()

    async for _event in service.send_message_stream(
        conversation.id,
        workspace_id=workspace_id,
        user_id=user_id,
        question="q",
        provider=_FakeProvider(),  # type: ignore[arg-type]
    ):
        pass
    await db_session.commit()

    history = await service._conversations.get_history(  # noqa: SLF001
        conversation.id, workspace_id=workspace_id, user_id=user_id
    )
    roles = [m.role for m in history]
    assert roles == [MessageRole.USER.value, MessageRole.ASSISTANT.value]


async def test_send_message_stream_does_not_persist_assistant_message_on_error(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    rag = _FakeRAGService(stream_events=[ErrorEvent(message="boom")])
    service = _session_service(db_session, rag=rag)
    conversation = await service.create_session(
        workspace_id=workspace_id, organization_id=organization_id, user_id=user_id
    )
    await db_session.commit()

    async for _event in service.send_message_stream(
        conversation.id,
        workspace_id=workspace_id,
        user_id=user_id,
        question="q",
        provider=_FakeProvider(),  # type: ignore[arg-type]
    ):
        pass
    await db_session.commit()

    history = await service._conversations.get_history(  # noqa: SLF001
        conversation.id, workspace_id=workspace_id, user_id=user_id
    )
    roles = [m.role for m in history]
    assert roles == [MessageRole.USER.value]


async def test_resume_returns_conversation_history_and_memory(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _session_service(db_session, rag=_FakeRAGService())
    conversation = await service.create_session(
        workspace_id=workspace_id, organization_id=organization_id, user_id=user_id
    )
    await db_session.commit()
    await service.send_message(
        conversation.id,
        workspace_id=workspace_id,
        user_id=user_id,
        question="q",
        provider=_FakeProvider(),  # type: ignore[arg-type]
    )
    await db_session.commit()

    resumed_conversation, history, memory = await service.resume(
        conversation.id, workspace_id=workspace_id, user_id=user_id
    )

    assert resumed_conversation.id == conversation.id
    assert len(history) == 2
    assert len(memory.recent_messages) == 2
