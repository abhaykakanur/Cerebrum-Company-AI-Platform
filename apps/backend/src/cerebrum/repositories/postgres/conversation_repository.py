"""``ConversationRepository``: CRUD, soft delete/restore, and text
search over
:class:`~cerebrum.infrastructure.database.models.conversation.Conversation`
— CIS Phase 4 Prompt 2's Conversation Management. Mirrors
cerebrum.repositories.postgres.document_repository.DocumentRepository's
exact shape.
"""

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.conversation import Conversation
from cerebrum.repositories.base import AbstractRepository
from cerebrum.repositories.contracts import FilterSpec, Page, Pagination, SortSpec
from cerebrum.repositories.postgres.query_utils import (
    apply_filters,
    apply_pagination,
    apply_sort,
)
from cerebrum.repositories.soft_delete import SoftDeleteRepository
from cerebrum.utils.clock import utcnow


class ConversationRepository(
    AbstractRepository[Conversation, uuid.UUID],
    SoftDeleteRepository[Conversation, uuid.UUID],
):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> Conversation | None:
        conversation = await self._session.get(Conversation, entity_id)
        return None if conversation is None or conversation.is_deleted else conversation

    async def get_by_id_including_deleted(
        self, entity_id: uuid.UUID
    ) -> Conversation | None:
        return await self._session.get(Conversation, entity_id)

    async def add(self, entity: Conversation) -> Conversation:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: Conversation) -> Conversation:
        await self._session.flush()
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        conversation = await self._session.get(Conversation, entity_id)
        if conversation is not None:
            await self._session.delete(conversation)
            await self._session.flush()

    async def soft_delete(self, entity_id: uuid.UUID) -> None:
        conversation = await self._session.get(Conversation, entity_id)
        if conversation is not None:
            conversation.is_deleted = True
            conversation.deleted_at = utcnow()
            await self._session.flush()

    async def restore(self, entity_id: uuid.UUID) -> None:
        conversation = await self._session.get(Conversation, entity_id)
        if conversation is not None:
            conversation.is_deleted = False
            conversation.deleted_at = None
            await self._session.flush()

    async def list(
        self,
        *,
        pagination: Pagination,
        filters: list[FilterSpec] | None = None,
        sort: list[SortSpec] | None = None,
    ) -> Page[Conversation]:
        base_statement = apply_filters(
            select(Conversation), Conversation, filters
        ).where(Conversation.is_deleted.is_(False))

        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = apply_sort(base_statement, Conversation, sort)
        statement = apply_pagination(statement, pagination)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)

    async def search_by_text(
        self, *, workspace_id: uuid.UUID, query_text: str, pagination: Pagination
    ) -> Page[Conversation]:
        """Title/summary substring search — the ``OR``-across-columns
        shape :func:`~cerebrum.repositories.postgres.query_utils.apply_filters`
        cannot express (it always combines filters with ``AND``), so
        this is a dedicated method rather than a generic filter.
        """
        base_statement = (
            select(Conversation)
            .where(Conversation.workspace_id == workspace_id)
            .where(Conversation.is_deleted.is_(False))
            .where(
                or_(
                    Conversation.title.contains(query_text),
                    Conversation.summary.contains(query_text),
                )
            )
        )

        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = base_statement.order_by(Conversation.updated_at.desc())
        statement = apply_pagination(statement, pagination)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)
