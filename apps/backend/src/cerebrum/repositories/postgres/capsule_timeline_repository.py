"""``CapsuleTimelineRepository``: append-mostly CRUD over
:class:`~cerebrum.infrastructure.database.models.capsule_timeline_event.CapsuleTimelineEvent`
— CIS Phase 5 Prompt 3's Organizational Timeline.
"""

import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.capsule_timeline_event import (
    CapsuleTimelineEvent,
)
from cerebrum.repositories.contracts import Page, Pagination


class CapsuleTimelineRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> CapsuleTimelineEvent | None:
        return await self._session.get(CapsuleTimelineEvent, entity_id)

    async def add(self, entity: CapsuleTimelineEvent) -> CapsuleTimelineEvent:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def replace_for_capsule(
        self, capsule_id: uuid.UUID, entities: list[CapsuleTimelineEvent]
    ) -> None:
        """A refresh rebuilds the whole timeline from the evidence the
        current refresh pass produced — rather than merging, every
        prior timeline event for this capsule is cleared first, so a
        capsule's timeline can never accumulate entries whose backing
        evidence has since been superseded.
        """
        statement = select(CapsuleTimelineEvent).where(
            CapsuleTimelineEvent.capsule_id == capsule_id
        )
        existing = list((await self._session.execute(statement)).scalars())
        for event in existing:
            await self._session.delete(event)
        await self._session.flush()
        for event in entities:
            self._session.add(event)
        await self._session.flush()

    async def list_by_capsule(
        self, capsule_id: uuid.UUID, *, pagination: Pagination
    ) -> Page[CapsuleTimelineEvent]:
        base_statement = select(CapsuleTimelineEvent).where(
            CapsuleTimelineEvent.capsule_id == capsule_id
        )
        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = base_statement.order_by(desc(CapsuleTimelineEvent.occurred_at))
        statement = statement.offset(pagination.offset).limit(pagination.page_size)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)
