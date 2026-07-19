"""Proves CIS Phase 4 Prompt 2's ``MessageRepository`` against a real
SQLite-backed session — same "test the real SQL" precedent
test_conversation_repository.py's docstring explains, including the
``citations`` JSON-substring search's portability across SQLite/
PostgreSQL.
"""

import uuid

import pytest
from _auth_factories import create_organization, create_user, create_workspace
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.conversation import Conversation
from cerebrum.infrastructure.database.models.message import Message
from cerebrum.repositories.contracts import Pagination
from cerebrum.repositories.postgres.conversation_repository import (
    ConversationRepository,
)
from cerebrum.repositories.postgres.message_repository import MessageRepository

pytestmark = pytest.mark.unit


async def _tenant_and_conversation(
    session: AsyncSession,
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
            title="Test conversation",
            status="active",
        )
    )
    await session.commit()
    return workspace.id, conversation


def _hasher():  # type: ignore[no-untyped-def]
    from cerebrum.config.security import SecuritySettings
    from cerebrum.infrastructure.security.password import PasswordHasher

    return PasswordHasher(SecuritySettings())


async def test_list_by_conversation_orders_by_sequence(
    db_session: AsyncSession,
) -> None:
    _workspace_id, conversation = await _tenant_and_conversation(db_session)
    repository = MessageRepository(db_session)
    for index in (2, 0, 1):
        await repository.add(
            Message(
                conversation_id=conversation.id,
                sequence_index=index,
                role="user",
                content=f"message {index}",
            )
        )
    await db_session.commit()

    messages = await repository.list_by_conversation(conversation.id)

    assert [m.sequence_index for m in messages] == [0, 1, 2]


async def test_list_by_conversation_after_sequence_excludes_earlier(
    db_session: AsyncSession,
) -> None:
    _workspace_id, conversation = await _tenant_and_conversation(db_session)
    repository = MessageRepository(db_session)
    for index in range(4):
        await repository.add(
            Message(
                conversation_id=conversation.id,
                sequence_index=index,
                role="user",
                content=f"message {index}",
            )
        )
    await db_session.commit()

    messages = await repository.list_by_conversation(conversation.id, after_sequence=1)

    assert [m.sequence_index for m in messages] == [2, 3]


async def test_count_by_conversation(db_session: AsyncSession) -> None:
    _workspace_id, conversation = await _tenant_and_conversation(db_session)
    repository = MessageRepository(db_session)
    for index in range(3):
        await repository.add(
            Message(
                conversation_id=conversation.id,
                sequence_index=index,
                role="user",
                content="hi",
            )
        )
    await db_session.commit()

    assert await repository.count_by_conversation(conversation.id) == 3


async def test_search_by_content_scoped_to_workspace(db_session: AsyncSession) -> None:
    workspace_id, conversation = await _tenant_and_conversation(db_session)
    _other_workspace_id, other_conversation = await _tenant_and_conversation(db_session)
    repository = MessageRepository(db_session)
    await repository.add(
        Message(
            conversation_id=conversation.id,
            sequence_index=0,
            role="user",
            content="What does Acme Corp make?",
        )
    )
    await repository.add(
        Message(
            conversation_id=other_conversation.id,
            sequence_index=0,
            role="user",
            content="Acme Corp is mentioned here too.",
        )
    )
    await db_session.commit()

    page = await repository.search_by_content(
        workspace_id=workspace_id,
        query_text="Acme Corp",
        pagination=Pagination(page=1, page_size=50),
    )

    assert page.total_items == 1
    assert page.items[0].conversation_id == conversation.id


async def test_search_by_citation_reference_finds_matching_document(
    db_session: AsyncSession,
) -> None:
    workspace_id, conversation = await _tenant_and_conversation(db_session)
    repository = MessageRepository(db_session)
    target_document_id = uuid.uuid4()
    await repository.add(
        Message(
            conversation_id=conversation.id,
            sequence_index=0,
            role="assistant",
            content="Here is the answer.",
            citations=[{"document_id": str(target_document_id), "confidence": 0.9}],
        )
    )
    await repository.add(
        Message(
            conversation_id=conversation.id,
            sequence_index=1,
            role="assistant",
            content="Unrelated answer.",
            citations=[{"document_id": str(uuid.uuid4()), "confidence": 0.9}],
        )
    )
    await db_session.commit()

    page = await repository.search_by_citation_reference(
        workspace_id=workspace_id,
        reference_id=target_document_id,
        pagination=Pagination(page=1, page_size=50),
    )

    assert page.total_items == 1
    assert page.items[0].sequence_index == 0
