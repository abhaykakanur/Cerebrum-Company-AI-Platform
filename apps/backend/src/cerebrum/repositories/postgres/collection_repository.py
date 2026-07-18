"""``CollectionRepository``: CRUD, soft delete/restore, and membership
operations over
:class:`~cerebrum.infrastructure.database.models.collection.Collection`
— CIS Phase 2 Prompt 1's Collections, extended by CIS Phase 2 Prompt 2's
bulk add/remove.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.collection import (
    Collection,
    CollectionDocument,
)
from cerebrum.repositories.base import AbstractRepository
from cerebrum.repositories.contracts import FilterSpec, Page, Pagination, SortSpec
from cerebrum.repositories.postgres.query_utils import (
    apply_filters,
    apply_pagination,
    apply_sort,
)
from cerebrum.repositories.soft_delete import SoftDeleteRepository
from cerebrum.utils.clock import utcnow


class CollectionRepository(
    AbstractRepository[Collection, uuid.UUID],
    SoftDeleteRepository[Collection, uuid.UUID],
):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> Collection | None:
        collection = await self._session.get(Collection, entity_id)
        return None if collection is None or collection.is_deleted else collection

    async def get_by_id_including_deleted(
        self, entity_id: uuid.UUID
    ) -> Collection | None:
        return await self._session.get(Collection, entity_id)

    async def get_by_name(
        self, *, workspace_id: uuid.UUID, name: str
    ) -> Collection | None:
        result = await self._session.execute(
            select(Collection).where(
                Collection.workspace_id == workspace_id,
                Collection.name == name,
                Collection.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def add(self, entity: Collection) -> Collection:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: Collection) -> Collection:
        await self._session.flush()
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        collection = await self.get_by_id_including_deleted(entity_id)
        if collection is not None:
            await self._session.delete(collection)
            await self._session.flush()

    async def soft_delete(self, entity_id: uuid.UUID) -> None:
        collection = await self.get_by_id_including_deleted(entity_id)
        if collection is not None:
            collection.is_deleted = True
            collection.deleted_at = utcnow()
            await self._session.flush()

    async def restore(self, entity_id: uuid.UUID) -> None:
        collection = await self.get_by_id_including_deleted(entity_id)
        if collection is not None:
            collection.is_deleted = False
            collection.deleted_at = None
            await self._session.flush()

    async def add_document(
        self, *, collection_id: uuid.UUID, document_id: uuid.UUID
    ) -> None:
        exists = await self._session.get(
            CollectionDocument, (collection_id, document_id)
        )
        if exists is None:
            self._session.add(
                CollectionDocument(
                    collection_id=collection_id,
                    document_id=document_id,
                    added_at=utcnow(),
                )
            )
            await self._session.flush()

    async def remove_document(
        self, *, collection_id: uuid.UUID, document_id: uuid.UUID
    ) -> None:
        link = await self._session.get(CollectionDocument, (collection_id, document_id))
        if link is not None:
            await self._session.delete(link)
            await self._session.flush()

    async def list_document_ids(
        self, collection_id: uuid.UUID, *, pagination: Pagination
    ) -> Page[uuid.UUID]:
        base_statement = select(CollectionDocument.document_id).where(
            CollectionDocument.collection_id == collection_id
        )
        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = base_statement.order_by(CollectionDocument.added_at.desc())
        statement = apply_pagination(statement, pagination)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)

    async def list(
        self,
        *,
        pagination: Pagination,
        filters: list[FilterSpec] | None = None,
        sort: list[SortSpec] | None = None,
    ) -> Page[Collection]:
        base_statement = apply_filters(select(Collection), Collection, filters).where(
            Collection.is_deleted.is_(False)
        )

        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = apply_sort(base_statement, Collection, sort)
        statement = apply_pagination(statement, pagination)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)
