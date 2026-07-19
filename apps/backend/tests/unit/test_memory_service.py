"""Proves CIS Phase 4 Prompt 2's ``MemoryService``: the rolling context
window (message-count and token-budget bounded), Context Pruning
(messages already folded into ``Conversation.summary`` are excluded),
retrieval-aware memory (previously-referenced document/entity ids), and
Citation Preservation — against real, SQLite-backed repositories.
"""

import uuid

import pytest
from _auth_factories import create_organization, create_user, create_workspace
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.conversation.memory_service import MemoryService
from cerebrum.infrastructure.database.models.conversation import Conversation
from cerebrum.infrastructure.database.models.message import Message, MessageRole
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


async def _conversation_with_messages(
    session: AsyncSession, messages: list[tuple[str, str, list[dict] | None]]
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
    for index, (role, content, citations) in enumerate(messages):
        await message_repository.add(
            Message(
                conversation_id=conversation.id,
                sequence_index=index,
                role=role,
                content=content,
                citations=citations or [],
                context_references=citations or [],
            )
        )
    await session.commit()
    return workspace.id, conversation


def _service(session: AsyncSession) -> MemoryService:
    return MemoryService(
        conversation_repository=ConversationRepository(session),
        message_repository=MessageRepository(session),
    )


async def test_build_memory_includes_all_recent_messages_within_limits(
    db_session: AsyncSession,
) -> None:
    workspace_id, conversation = await _conversation_with_messages(
        db_session,
        [
            (MessageRole.USER.value, "What does Acme make?", None),
            (MessageRole.ASSISTANT.value, "Widgets.", None),
        ],
    )
    service = _service(db_session)

    memory = await service.build_memory(conversation.id, workspace_id=workspace_id)

    assert [m.content for m in memory.recent_messages] == [
        "What does Acme make?",
        "Widgets.",
    ]
    assert memory.truncated is False


async def test_build_memory_excludes_summarized_messages(
    db_session: AsyncSession,
) -> None:
    workspace_id, conversation = await _conversation_with_messages(
        db_session,
        [
            (MessageRole.USER.value, "old question", None),
            (MessageRole.ASSISTANT.value, "old answer", None),
            (MessageRole.USER.value, "new question", None),
        ],
    )
    conversation.summary = "Earlier the user asked an old question."
    conversation.summarized_through_sequence = 1
    await ConversationRepository(db_session).update(conversation)
    await db_session.commit()
    service = _service(db_session)

    memory = await service.build_memory(conversation.id, workspace_id=workspace_id)

    assert [m.content for m in memory.recent_messages] == ["new question"]
    assert memory.summary == "Earlier the user asked an old question."


async def test_build_memory_respects_max_messages_window(
    db_session: AsyncSession,
) -> None:
    workspace_id, conversation = await _conversation_with_messages(
        db_session,
        [(MessageRole.USER.value, f"message {i}", None) for i in range(5)],
    )
    service = _service(db_session)

    memory = await service.build_memory(
        conversation.id, workspace_id=workspace_id, max_messages=2
    )

    assert [m.content for m in memory.recent_messages] == ["message 3", "message 4"]
    assert memory.truncated is True


async def test_build_memory_respects_token_budget(db_session: AsyncSession) -> None:
    workspace_id, conversation = await _conversation_with_messages(
        db_session,
        [
            (MessageRole.USER.value, "x" * 100, None),
            (MessageRole.ASSISTANT.value, "y" * 100, None),
        ],
    )
    service = _service(db_session)

    # 10 tokens * 4 chars/token = 40 char budget: the most recent
    # message alone (100 chars) already exceeds it, so only that one
    # is kept (never zero — see MemoryService's rolling-window helper).
    memory = await service.build_memory(
        conversation.id, workspace_id=workspace_id, max_tokens=10
    )

    assert len(memory.recent_messages) == 1
    assert memory.recent_messages[0].content == "y" * 100
    assert memory.truncated is True


async def test_build_memory_collects_carried_citations_from_assistant_messages(
    db_session: AsyncSession,
) -> None:
    citation = {"document_id": str(uuid.uuid4()), "confidence": 0.9}
    workspace_id, conversation = await _conversation_with_messages(
        db_session,
        [
            (MessageRole.USER.value, "question", None),
            (MessageRole.ASSISTANT.value, "answer", [citation]),
        ],
    )
    service = _service(db_session)

    memory = await service.build_memory(conversation.id, workspace_id=workspace_id)

    assert memory.carried_citations == [citation]


async def test_build_memory_collects_previously_referenced_ids(
    db_session: AsyncSession,
) -> None:
    document_id = uuid.uuid4()
    entity_id = uuid.uuid4()
    reference = {"document_id": str(document_id), "entity_id": str(entity_id)}
    workspace_id, conversation = await _conversation_with_messages(
        db_session,
        [(MessageRole.ASSISTANT.value, "answer", [reference])],
    )
    service = _service(db_session)

    memory = await service.build_memory(conversation.id, workspace_id=workspace_id)

    assert memory.previously_referenced_document_ids == {str(document_id)}
    assert memory.previously_referenced_entity_ids == {str(entity_id)}


async def test_as_llm_messages_puts_summary_first_then_recent_turns(
    db_session: AsyncSession,
) -> None:
    workspace_id, conversation = await _conversation_with_messages(
        db_session, [(MessageRole.USER.value, "hello", None)]
    )
    conversation.summary = "Prior discussion summary."
    await ConversationRepository(db_session).update(conversation)
    await db_session.commit()
    service = _service(db_session)

    memory = await service.build_memory(conversation.id, workspace_id=workspace_id)
    llm_messages = memory.as_llm_messages()

    assert llm_messages[0].role == "system"
    assert "Prior discussion summary." in llm_messages[0].content
    assert llm_messages[1].role == "user"
    assert llm_messages[1].content == "hello"


async def test_build_memory_raises_not_found_for_wrong_workspace(
    db_session: AsyncSession,
) -> None:
    _workspace_id, conversation = await _conversation_with_messages(db_session, [])
    service = _service(db_session)

    with pytest.raises(NotFoundException):
        await service.build_memory(conversation.id, workspace_id=uuid.uuid4())
