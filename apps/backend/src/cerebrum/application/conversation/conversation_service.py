"""``ConversationService``: CRUD, lifecycle (archive/delete), history,
search, and export over
:class:`~cerebrum.infrastructure.database.models.conversation.Conversation`/
:class:`~cerebrum.infrastructure.database.models.message.Message` — CIS
Phase 4 Prompt 2's Conversation Management, Conversation Model, and
Message Model. Mirrors
cerebrum.application.knowledge.document_service.DocumentService's exact
shape (create/get/rename/change_status/soft_delete/restore/list_in_workspace).

Every conversation-scoped method funnels through :meth:`get`, which
enforces both Workspace Isolation (``workspace_id`` match) and User
Ownership (``user_id`` match, CIS Phase 4 Prompt 2's Security
requirement) in one place — a conversation is private to the user who
created it; there is no sharing/ACL model in this milestone's scope.
"""

import uuid
from typing import Any

from cerebrum.application.conversation.events import (
    ConversationArchivedEvent,
    ConversationCreatedEvent,
    MessageAddedEvent,
)
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.conversation import (
    Conversation,
    ConversationStatus,
)
from cerebrum.infrastructure.database.models.message import Message, MessageRole
from cerebrum.repositories.contracts import (
    FilterOperator,
    FilterSpec,
    Page,
    Pagination,
    SortDirection,
    SortSpec,
)
from cerebrum.repositories.postgres.conversation_repository import (
    ConversationRepository,
)
from cerebrum.repositories.postgres.message_repository import MessageRepository
from cerebrum.shared.errors.exceptions import (
    NotFoundException,
    PermissionDeniedException,
)

_DEFAULT_TITLE = "New Conversation"
_TITLE_MAX_LENGTH = 500


class ConversationService:
    def __init__(
        self,
        *,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._conversations = conversation_repository
        self._messages = message_repository
        self._events = event_dispatcher

    async def create(
        self,
        *,
        workspace_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Conversation:
        conversation = Conversation(
            workspace_id=workspace_id,
            organization_id=organization_id,
            user_id=user_id,
            session_id=session_id,
            title=(title or _DEFAULT_TITLE)[:_TITLE_MAX_LENGTH],
            status=ConversationStatus.ACTIVE.value,
            conversation_metadata=metadata or {},
            created_by=user_id,
            updated_by=user_id,
        )
        created = await self._conversations.add(conversation)
        self._events.publish(
            ConversationCreatedEvent(
                conversation_id=created.id, workspace_id=workspace_id, user_id=user_id
            )
        )
        return created

    async def get(
        self, conversation_id: uuid.UUID, *, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> Conversation:
        conversation = await self._conversations.get_by_id(conversation_id)
        if conversation is None or conversation.workspace_id != workspace_id:
            raise NotFoundException(f"No conversation with id {conversation_id}.")
        if conversation.user_id != user_id:
            raise PermissionDeniedException(
                "You do not own this conversation.",
                context={"conversation_id": str(conversation_id)},
            )
        return conversation

    async def rename(
        self,
        conversation_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str,
    ) -> Conversation:
        conversation = await self.get(
            conversation_id, workspace_id=workspace_id, user_id=user_id
        )
        conversation.title = title[:_TITLE_MAX_LENGTH]
        conversation.updated_by = user_id
        return await self._conversations.update(conversation)

    async def archive(
        self, conversation_id: uuid.UUID, *, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> Conversation:
        conversation = await self.get(
            conversation_id, workspace_id=workspace_id, user_id=user_id
        )
        conversation.status = ConversationStatus.ARCHIVED.value
        conversation.updated_by = user_id
        updated = await self._conversations.update(conversation)
        self._events.publish(
            ConversationArchivedEvent(
                conversation_id=conversation.id, workspace_id=workspace_id
            )
        )
        return updated

    async def delete(
        self, conversation_id: uuid.UUID, *, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        conversation = await self.get(
            conversation_id, workspace_id=workspace_id, user_id=user_id
        )
        conversation.status = ConversationStatus.DELETED.value
        conversation.updated_by = user_id
        await self._conversations.update(conversation)
        await self._conversations.soft_delete(conversation_id)

    async def list_in_workspace(
        self,
        *,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        pagination: Pagination,
        status: ConversationStatus | None = None,
    ) -> Page[Conversation]:
        filters = [
            FilterSpec(
                field="workspace_id", operator=FilterOperator.EQ, value=workspace_id
            ),
            FilterSpec(field="user_id", operator=FilterOperator.EQ, value=user_id),
        ]
        if status is not None:
            filters.append(
                FilterSpec(
                    field="status", operator=FilterOperator.EQ, value=status.value
                )
            )
        return await self._conversations.list(
            pagination=pagination,
            filters=filters,
            sort=[SortSpec(field="updated_at", direction=SortDirection.DESC)],
        )

    async def search_conversations(
        self, *, workspace_id: uuid.UUID, query_text: str, pagination: Pagination
    ) -> Page[Conversation]:
        return await self._conversations.search_by_text(
            workspace_id=workspace_id, query_text=query_text, pagination=pagination
        )

    async def search_messages(
        self, *, workspace_id: uuid.UUID, query_text: str, pagination: Pagination
    ) -> Page[Message]:
        return await self._messages.search_by_content(
            workspace_id=workspace_id, query_text=query_text, pagination=pagination
        )

    async def search_by_reference(
        self,
        *,
        workspace_id: uuid.UUID,
        reference_id: uuid.UUID,
        pagination: Pagination,
    ) -> Page[Message]:
        """Search by citation, entity, or document — all three are the
        same lookup (a UUID that may appear as a citation's
        ``document_id``, ``entity_id``, or ``chunk_id``) — see
        cerebrum.repositories.postgres.message_repository.MessageRepository.search_by_citation_reference.
        """
        return await self._messages.search_by_citation_reference(
            workspace_id=workspace_id, reference_id=reference_id, pagination=pagination
        )

    async def get_history(
        self, conversation_id: uuid.UUID, *, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[Message]:
        await self.get(conversation_id, workspace_id=workspace_id, user_id=user_id)
        return await self._messages.list_by_conversation(conversation_id)

    async def add_message(
        self,
        conversation_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        role: MessageRole,
        content: str,
        citations: list[dict[str, Any]] | None = None,
        context_references: list[dict[str, Any]] | None = None,
        confidence: float | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> Message:
        """Does not itself check ownership — callers that already hold
        a validated ``Conversation`` (e.g.
        cerebrum.application.conversation.session_service.SessionService,
        mid-turn) pass its id directly rather than paying for a second
        :meth:`get` round trip; still validates the conversation exists
        in this workspace, so a mismatched ``conversation_id`` fails
        loudly rather than silently orphaning a message.
        """
        conversation = await self._conversations.get_by_id(conversation_id)
        if conversation is None or conversation.workspace_id != workspace_id:
            raise NotFoundException(f"No conversation with id {conversation_id}.")

        next_sequence = await self._messages.count_by_conversation(conversation_id)
        message = Message(
            conversation_id=conversation_id,
            sequence_index=next_sequence,
            role=role.value,
            content=content,
            citations=citations or [],
            context_references=context_references or [],
            confidence=confidence,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        created = await self._messages.add(message)

        conversation.last_message_at = created.created_at
        await self._conversations.update(conversation)

        self._events.publish(
            MessageAddedEvent(
                conversation_id=conversation_id,
                workspace_id=workspace_id,
                message_id=created.id,
                role=role.value,
            )
        )
        return created

    async def export(
        self, conversation_id: uuid.UUID, *, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> dict[str, Any]:
        conversation = await self.get(
            conversation_id, workspace_id=workspace_id, user_id=user_id
        )
        messages = await self._messages.list_by_conversation(conversation_id)
        return {
            "conversation": {
                "id": str(conversation.id),
                "title": conversation.title,
                "status": conversation.status,
                "summary": conversation.summary,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
                "metadata": conversation.conversation_metadata,
            },
            "messages": [
                {
                    "id": str(message.id),
                    "sequence_index": message.sequence_index,
                    "role": message.role,
                    "content": message.content,
                    "citations": message.citations,
                    "context_references": message.context_references,
                    "confidence": message.confidence,
                    "prompt_tokens": message.prompt_tokens,
                    "completion_tokens": message.completion_tokens,
                    "created_at": message.created_at.isoformat(),
                }
                for message in messages
            ],
        }
