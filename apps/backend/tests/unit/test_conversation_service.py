"""Proves CIS Phase 4 Prompt 2's ``ConversationService``: lifecycle
(create/rename/archive/delete), Workspace Isolation and User Ownership
enforcement (both funnel through :meth:`~ConversationService.get`),
message persistence (sequence assignment, ``last_message_at``), history,
export, and event publication — against real, SQLite-backed
repositories (see test_conversation_repository.py's docstring for why).
"""

import uuid

import pytest
from _auth_factories import create_organization, create_user, create_workspace
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.conversation.conversation_service import ConversationService
from cerebrum.application.conversation.events import (
    ConversationArchivedEvent,
    ConversationCreatedEvent,
    MessageAddedEvent,
)
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.conversation import ConversationStatus
from cerebrum.infrastructure.database.models.message import MessageRole
from cerebrum.repositories.contracts import Pagination
from cerebrum.repositories.postgres.conversation_repository import (
    ConversationRepository,
)
from cerebrum.repositories.postgres.message_repository import MessageRepository
from cerebrum.shared.errors.exceptions import (
    NotFoundException,
    PermissionDeniedException,
)

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


def _service(
    session: AsyncSession, *, events: EventDispatcher | None = None
) -> ConversationService:
    return ConversationService(
        conversation_repository=ConversationRepository(session),
        message_repository=MessageRepository(session),
        event_dispatcher=events or EventDispatcher(),
    )


async def test_create_publishes_conversation_created_event(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    events = EventDispatcher()
    received: list[ConversationCreatedEvent] = []
    events.subscribe(ConversationCreatedEvent, received.append)
    service = _service(db_session, events=events)

    conversation = await service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        title="Q1 Planning",
    )
    await db_session.commit()

    assert conversation.title == "Q1 Planning"
    assert conversation.status == ConversationStatus.ACTIVE.value
    assert len(received) == 1
    assert received[0].conversation_id == conversation.id


async def test_create_defaults_title_when_omitted(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)

    conversation = await service.create(
        workspace_id=workspace_id, organization_id=organization_id, user_id=user_id
    )
    await db_session.commit()

    assert conversation.title == "New Conversation"


async def test_get_raises_not_found_for_wrong_workspace(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    conversation = await service.create(
        workspace_id=workspace_id, organization_id=organization_id, user_id=user_id
    )
    await db_session.commit()

    with pytest.raises(NotFoundException):
        await service.get(conversation.id, workspace_id=uuid.uuid4(), user_id=user_id)


async def test_get_raises_permission_denied_for_non_owner(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    conversation = await service.create(
        workspace_id=workspace_id, organization_id=organization_id, user_id=user_id
    )
    await db_session.commit()

    with pytest.raises(PermissionDeniedException):
        await service.get(
            conversation.id, workspace_id=workspace_id, user_id=uuid.uuid4()
        )


async def test_rename_updates_title(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    conversation = await service.create(
        workspace_id=workspace_id, organization_id=organization_id, user_id=user_id
    )
    await db_session.commit()

    renamed = await service.rename(
        conversation.id, workspace_id=workspace_id, user_id=user_id, title="New title"
    )
    await db_session.commit()

    assert renamed.title == "New title"


async def test_archive_sets_status_and_publishes_event(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    events = EventDispatcher()
    received: list[ConversationArchivedEvent] = []
    events.subscribe(ConversationArchivedEvent, received.append)
    service = _service(db_session, events=events)
    conversation = await service.create(
        workspace_id=workspace_id, organization_id=organization_id, user_id=user_id
    )
    await db_session.commit()

    archived = await service.archive(
        conversation.id, workspace_id=workspace_id, user_id=user_id
    )
    await db_session.commit()

    assert archived.status == ConversationStatus.ARCHIVED.value
    assert len(received) == 1


async def test_delete_soft_deletes_the_conversation(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    conversation = await service.create(
        workspace_id=workspace_id, organization_id=organization_id, user_id=user_id
    )
    await db_session.commit()

    await service.delete(conversation.id, workspace_id=workspace_id, user_id=user_id)
    await db_session.commit()

    with pytest.raises(NotFoundException):
        await service.get(conversation.id, workspace_id=workspace_id, user_id=user_id)


async def test_list_in_workspace_scoped_to_user_and_status(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    _org2, _ws2, other_user_id = await _tenant(db_session)
    service = _service(db_session)
    mine = await service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        title="Mine",
    )
    await service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=other_user_id,
        title="Not mine",
    )
    await db_session.commit()
    await service.archive(mine.id, workspace_id=workspace_id, user_id=user_id)
    await db_session.commit()

    active_page = await service.list_in_workspace(
        workspace_id=workspace_id,
        user_id=user_id,
        pagination=Pagination(page=1, page_size=50),
        status=ConversationStatus.ACTIVE,
    )
    all_page = await service.list_in_workspace(
        workspace_id=workspace_id,
        user_id=user_id,
        pagination=Pagination(page=1, page_size=50),
    )

    assert active_page.total_items == 0
    assert [c.id for c in all_page.items] == [mine.id]


async def test_add_message_assigns_sequence_and_updates_last_message_at(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    conversation = await service.create(
        workspace_id=workspace_id, organization_id=organization_id, user_id=user_id
    )
    await db_session.commit()

    first = await service.add_message(
        conversation.id,
        workspace_id=workspace_id,
        role=MessageRole.USER,
        content="Hello",
    )
    second = await service.add_message(
        conversation.id,
        workspace_id=workspace_id,
        role=MessageRole.ASSISTANT,
        content="Hi there",
        confidence=0.8,
    )
    await db_session.commit()

    assert first.sequence_index == 0
    assert second.sequence_index == 1
    refreshed = await service.get(
        conversation.id, workspace_id=workspace_id, user_id=user_id
    )
    assert refreshed.last_message_at == second.created_at


async def test_add_message_publishes_message_added_event(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    events = EventDispatcher()
    received: list[MessageAddedEvent] = []
    events.subscribe(MessageAddedEvent, received.append)
    service = _service(db_session, events=events)
    conversation = await service.create(
        workspace_id=workspace_id, organization_id=organization_id, user_id=user_id
    )
    await db_session.commit()

    await service.add_message(
        conversation.id,
        workspace_id=workspace_id,
        role=MessageRole.USER,
        content="Hello",
    )
    await db_session.commit()

    assert len(received) == 1
    assert received[0].role == "user"


async def test_get_history_returns_messages_in_order(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    conversation = await service.create(
        workspace_id=workspace_id, organization_id=organization_id, user_id=user_id
    )
    await db_session.commit()
    await service.add_message(
        conversation.id, workspace_id=workspace_id, role=MessageRole.USER, content="Q1"
    )
    await service.add_message(
        conversation.id,
        workspace_id=workspace_id,
        role=MessageRole.ASSISTANT,
        content="A1",
    )
    await db_session.commit()

    history = await service.get_history(
        conversation.id, workspace_id=workspace_id, user_id=user_id
    )

    assert [m.content for m in history] == ["Q1", "A1"]


async def test_export_returns_conversation_and_messages(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    conversation = await service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        title="Exported",
    )
    await db_session.commit()
    await service.add_message(
        conversation.id, workspace_id=workspace_id, role=MessageRole.USER, content="Q1"
    )
    await db_session.commit()

    export = await service.export(
        conversation.id, workspace_id=workspace_id, user_id=user_id
    )

    assert export["conversation"]["title"] == "Exported"
    assert len(export["messages"]) == 1
    assert export["messages"][0]["content"] == "Q1"
