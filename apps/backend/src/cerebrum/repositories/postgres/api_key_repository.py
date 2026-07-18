"""``APIKeyRepository``: API key storage and lookup."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.api_key import APIKey
from cerebrum.repositories.base import AbstractRepository
from cerebrum.repositories.contracts import FilterSpec, Page, Pagination, SortSpec
from cerebrum.repositories.postgres.query_utils import apply_filters, apply_sort


class APIKeyRepository(AbstractRepository[APIKey, uuid.UUID]):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> APIKey | None:
        return await self._session.get(APIKey, entity_id)

    async def get_by_hashed_key(self, hashed_key: str) -> APIKey | None:
        """The validation-path lookup: the raw key presented by a caller
        is hashed first (see cerebrum.application.auth.api_key_service),
        then looked up here — the raw key itself is never queried or
        stored, per :class:`~cerebrum.infrastructure.database.models.api_key.APIKey`'s
        docstring.
        """
        statement = select(APIKey).where(APIKey.hashed_key == hashed_key)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID) -> list[APIKey]:
        statement = select(APIKey).where(APIKey.user_id == user_id)
        result = await self._session.execute(statement)
        return list(result.scalars())

    async def add(self, entity: APIKey) -> APIKey:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: APIKey) -> APIKey:
        await self._session.flush()
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        api_key = await self.get_by_id(entity_id)
        if api_key is not None:
            await self._session.delete(api_key)
            await self._session.flush()

    async def list(
        self,
        *,
        pagination: Pagination,
        filters: list[FilterSpec] | None = None,
        sort: list[SortSpec] | None = None,
    ) -> Page[APIKey]:
        base_statement = apply_filters(select(APIKey), APIKey, filters)

        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = apply_sort(base_statement, APIKey, sort)
        statement = statement.offset(pagination.offset).limit(pagination.page_size)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)
