"""``UserSessionRepository``: refresh-token/session tracking storage."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.session import UserSession
from cerebrum.repositories.base import AbstractRepository
from cerebrum.repositories.contracts import FilterSpec, Page, Pagination, SortSpec
from cerebrum.repositories.postgres.query_utils import apply_filters, apply_sort


class UserSessionRepository(AbstractRepository[UserSession, uuid.UUID]):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> UserSession | None:
        return await self._session.get(UserSession, entity_id)

    async def get_by_refresh_token_hash(
        self, refresh_token_hash: str
    ) -> UserSession | None:
        statement = select(UserSession).where(
            UserSession.refresh_token_hash == refresh_token_hash
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_active_for_user(self, user_id: uuid.UUID) -> list[UserSession]:
        """Every non-revoked, non-expired session for ``user_id`` — the
        query a future "active sessions" view or a mass-logout-all-devices
        action would use. ``UserSession.is_active`` is a Python
        property, so filtering happens after the DB round-trip rather
        than as SQL — acceptable at this milestone's scale (a user's own
        session count is small); a heavier query would push the
        expiry/revocation comparison into the ``WHERE`` clause instead.
        """
        statement = select(UserSession).where(UserSession.user_id == user_id)
        result = await self._session.execute(statement)
        return [session for session in result.scalars() if session.is_active]

    async def add(self, entity: UserSession) -> UserSession:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: UserSession) -> UserSession:
        await self._session.flush()
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        session_row = await self.get_by_id(entity_id)
        if session_row is not None:
            await self._session.delete(session_row)
            await self._session.flush()

    async def list(
        self,
        *,
        pagination: Pagination,
        filters: list[FilterSpec] | None = None,
        sort: list[SortSpec] | None = None,
    ) -> Page[UserSession]:
        base_statement = apply_filters(select(UserSession), UserSession, filters)

        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = apply_sort(base_statement, UserSession, sort)
        statement = statement.offset(pagination.offset).limit(pagination.page_size)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)
