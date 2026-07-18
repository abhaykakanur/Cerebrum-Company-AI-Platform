"""``UserRepository``: the first concrete implementation of
:class:`~cerebrum.repositories.base.AbstractRepository`.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.user import User
from cerebrum.repositories.base import AbstractRepository
from cerebrum.repositories.contracts import FilterSpec, Page, Pagination, SortSpec
from cerebrum.repositories.postgres.query_utils import apply_filters, apply_sort


class UserRepository(AbstractRepository[User, uuid.UUID]):
    """Constructed with a session — supplied by a
    :class:`~cerebrum.infrastructure.database.unit_of_work.UnitOfWork`
    or the per-request session dependency, per
    docs/architecture/infrastructure/repository-guide.md. Never owns or
    closes the session itself.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> User | None:
        return await self._session.get(User, entity_id)

    async def get_by_email(self, email: str) -> User | None:
        """Not part of :class:`AbstractRepository`'s generic contract —
        a repository-specific query, as expected per
        docs/architecture/infrastructure/repository-guide.md.
        """
        statement = select(User).where(func.lower(User.email) == email.lower())
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def add(self, entity: User) -> User:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: User) -> User:
        await self._session.flush()
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        user = await self.get_by_id(entity_id)
        if user is not None:
            await self._session.delete(user)
            await self._session.flush()

    async def list(
        self,
        *,
        pagination: Pagination,
        filters: list[FilterSpec] | None = None,
        sort: list[SortSpec] | None = None,
    ) -> Page[User]:
        base_statement = apply_filters(select(User), User, filters)

        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = apply_sort(base_statement, User, sort)
        statement = statement.offset(pagination.offset).limit(pagination.page_size)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)
