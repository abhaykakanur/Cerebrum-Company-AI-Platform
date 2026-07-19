"""Proves CIS Phase 4 Prompt 2's ``ConversationSummaryService``:
Automatic Conversation Summarization only fires once the unsummarized
message count reaches its threshold, leaves the most recent messages
out of the summary (Context Pruning), reuses CIS Phase 4 Prompt 1's
``LLMProvider`` abstraction for the summarization call itself (a fake
provider here, real HTTP-based providers already proven in
test_llm_providers.py), and publishes ``ConversationSummarizedEvent``.
"""

import uuid
from collections.abc import AsyncGenerator

import pytest
from _auth_factories import create_organization, create_user, create_workspace
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.conversation.conversation_summary_service import (
    ConversationSummaryService,
)
from cerebrum.application.conversation.events import ConversationSummarizedEvent
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.conversation import Conversation
from cerebrum.infrastructure.database.models.message import Message, MessageRole
from cerebrum.infrastructure.llm.provider import LLMMessage, LLMResponse, LLMUsage
from cerebrum.repositories.postgres.conversation_repository import (
    ConversationRepository,
)
from cerebrum.repositories.postgres.message_repository import MessageRepository
from cerebrum.shared.errors.exceptions import NotFoundException

pytestmark = pytest.mark.unit


def _hasher():  # type: ignore[no-untyped-def]
    from cerebrum.config.security import SecuritySettings
    from cerebrum.infrastructure.security.password import PasswordHasher

    return PasswordHasher(SecuritySettings())


class _FakeProvider:
    name = "fake"
    default_model = "fake-model"

    def __init__(self, summary_text: str = "Concise summary.") -> None:
        self.summary_text = summary_text
        self.last_prompt: list[LLMMessage] = []

    async def generate(
        self, messages: list[LLMMessage], **kwargs: object
    ) -> LLMResponse:
        self.last_prompt = messages
        return LLMResponse(
            content=self.summary_text,
            model=self.default_model,
            provider=self.name,
            usage=LLMUsage(prompt_tokens=10, completion_tokens=5),
        )

    async def stream(
        self, messages: list[LLMMessage], **kwargs: object
    ) -> AsyncGenerator[str, None]:
        raise NotImplementedError
        yield ""  # pragma: no cover


async def _conversation_with_messages(
    session: AsyncSession, message_count: int
) -> tuple[uuid.UUID, Conversation]:
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
    conversation = await ConversationRepository(session).add(
        Conversation(
            workspace_id=workspace.id,
            organization_id=org.id,
            user_id=user.id,
            title="Test",
            status="active",
        )
    )
    await session.commit()

    message_repository = MessageRepository(session)
    for index in range(message_count):
        role = MessageRole.USER.value if index % 2 == 0 else MessageRole.ASSISTANT.value
        await message_repository.add(
            Message(
                conversation_id=conversation.id,
                sequence_index=index,
                role=role,
                content=f"message {index}",
            )
        )
    await session.commit()
    return workspace.id, conversation


def _service(
    session: AsyncSession, *, events: EventDispatcher | None = None
) -> ConversationSummaryService:
    return ConversationSummaryService(
        conversation_repository=ConversationRepository(session),
        message_repository=MessageRepository(session),
        event_dispatcher=events or EventDispatcher(),
    )


async def test_returns_none_below_threshold(db_session: AsyncSession) -> None:
    workspace_id, conversation = await _conversation_with_messages(db_session, 5)
    service = _service(db_session)

    result = await service.maybe_summarize(
        conversation.id,
        workspace_id=workspace_id,
        provider=_FakeProvider(),
        threshold=20,
    )

    assert result is None


async def test_summarizes_and_prunes_when_threshold_reached(
    db_session: AsyncSession,
) -> None:
    workspace_id, conversation = await _conversation_with_messages(db_session, 10)
    service = _service(db_session)
    provider = _FakeProvider(summary_text="Users discussed Acme Corp's product line.")

    updated = await service.maybe_summarize(
        conversation.id,
        workspace_id=workspace_id,
        provider=provider,
        threshold=8,
        keep_recent=3,
    )

    assert updated is not None
    assert updated.summary == "Users discussed Acme Corp's product line."
    # 10 messages, keep_recent=3 -> summarized indices 0..6, so
    # summarized_through_sequence lands on index 6.
    assert updated.summarized_through_sequence == 6


async def test_leaves_recent_messages_available_for_a_later_run(
    db_session: AsyncSession,
) -> None:
    workspace_id, conversation = await _conversation_with_messages(db_session, 10)
    service = _service(db_session)

    await service.maybe_summarize(
        conversation.id,
        workspace_id=workspace_id,
        provider=_FakeProvider(),
        threshold=8,
        keep_recent=3,
    )

    unsummarized = await MessageRepository(db_session).list_by_conversation(
        conversation.id, after_sequence=6
    )
    assert [m.sequence_index for m in unsummarized] == [7, 8, 9]


async def test_publishes_conversation_summarized_event(
    db_session: AsyncSession,
) -> None:
    workspace_id, conversation = await _conversation_with_messages(db_session, 10)
    events = EventDispatcher()
    received: list[ConversationSummarizedEvent] = []
    events.subscribe(ConversationSummarizedEvent, received.append)
    service = _service(db_session, events=events)

    await service.maybe_summarize(
        conversation.id,
        workspace_id=workspace_id,
        provider=_FakeProvider(),
        threshold=8,
        keep_recent=3,
    )

    assert len(received) == 1
    assert received[0].conversation_id == conversation.id
    assert received[0].summarized_through_sequence == 6


async def test_prepends_existing_summary_into_the_prompt(
    db_session: AsyncSession,
) -> None:
    workspace_id, conversation = await _conversation_with_messages(db_session, 10)
    conversation.summary = "Earlier summary text."
    await ConversationRepository(db_session).update(conversation)
    await db_session.commit()
    service = _service(db_session)
    provider = _FakeProvider()

    await service.maybe_summarize(
        conversation.id,
        workspace_id=workspace_id,
        provider=provider,
        threshold=8,
        keep_recent=3,
    )

    user_prompt = provider.last_prompt[-1].content
    assert "Earlier summary text." in user_prompt


async def test_raises_not_found_for_wrong_workspace(db_session: AsyncSession) -> None:
    _workspace_id, conversation = await _conversation_with_messages(db_session, 10)
    service = _service(db_session)

    with pytest.raises(NotFoundException):
        await service.maybe_summarize(
            conversation.id, workspace_id=uuid.uuid4(), provider=_FakeProvider()
        )
