"""``MessageRepository``: append-only CRUD over
:class:`~cerebrum.infrastructure.database.models.message.Message` —
CIS Phase 4 Prompt 2's Message Model persistence. Many rows per
conversation; mirrors
cerebrum.repositories.postgres.chunk_repository.ChunkRepository's
shape (no ``workspace_id``/``organization_id`` column here either — a
message is always reached through its already workspace-validated
:class:`~cerebrum.infrastructure.database.models.conversation.Conversation`,
the same "child scoped via its parent, not denormalized tenant
columns" precedent ``Chunk`` established for
``DocumentVersion``/``Document``).

:meth:`search_by_content`/:meth:`search_by_citation_reference` join
back to ``Conversation`` for workspace scoping precisely because those
two methods search *across* conversations, unlike
:meth:`list_by_conversation` (already scoped by a caller-supplied,
already-workspace-validated ``conversation_id``).
"""

import uuid

from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.conversation import Conversation
from cerebrum.infrastructure.database.models.message import Message
from cerebrum.repositories.contracts import Page, Pagination
from cerebrum.repositories.postgres.query_utils import apply_pagination


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> Message | None:
        return await self._session.get(Message, entity_id)

    async def add(self, entity: Message) -> Message:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def list_by_conversation(
        self, conversation_id: uuid.UUID, *, after_sequence: int | None = None
    ) -> list[Message]:
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence_index)
        )
        if after_sequence is not None:
            statement = statement.where(Message.sequence_index > after_sequence)
        result = await self._session.execute(statement)
        return list(result.scalars())

    async def count_by_conversation(self, conversation_id: uuid.UUID) -> int:
        statement = select(func.count()).where(
            Message.conversation_id == conversation_id
        )
        return (await self._session.execute(statement)).scalar_one()

    async def search_by_content(
        self, *, workspace_id: uuid.UUID, query_text: str, pagination: Pagination
    ) -> Page[Message]:
        base_statement = (
            select(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(Conversation.workspace_id == workspace_id)
            .where(Conversation.is_deleted.is_(False))
            .where(Message.content.contains(query_text))
        )

        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = base_statement.order_by(Message.created_at.desc())
        statement = apply_pagination(statement, pagination)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)

    async def search_by_citation_reference(
        self,
        *,
        workspace_id: uuid.UUID,
        reference_id: uuid.UUID,
        pagination: Pagination,
    ) -> Page[Message]:
        """Search by citation/entity/document — a single method for all
        three, since a citation reference is a document id, an entity
        id, or (via ``document_id``) implicitly a document search; the
        caller passes whichever id it is searching for.

        A substring match against the serialized ``citations`` JSON
        column, not a native JSONB containment query (``@>``) —
        deliberately portable across PostgreSQL and this suite's SQLite
        test harness (see apps/backend/tests/conftest.py's ``db_engine``
        fixture), at the honestly-documented cost of matching the UUID
        string anywhere in the column rather than only within a
        specific citation key — acceptable since a UUIDv4 string is
        practically never a substring collision.
        """
        pattern = f"%{reference_id}%"
        base_statement = (
            select(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(Conversation.workspace_id == workspace_id)
            .where(Conversation.is_deleted.is_(False))
            .where(cast(Message.citations, String).contains(pattern))
        )

        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = base_statement.order_by(Message.created_at.desc())
        statement = apply_pagination(statement, pagination)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)
