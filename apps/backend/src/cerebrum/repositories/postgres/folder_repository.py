"""``FolderRepository``: CRUD, soft delete/restore, and hierarchy queries
over :class:`~cerebrum.infrastructure.database.models.folder.Folder` —
CIS Phase 2 Prompt 1's Folder System.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.folder import Folder
from cerebrum.repositories.base import AbstractRepository
from cerebrum.repositories.contracts import FilterSpec, Page, Pagination, SortSpec
from cerebrum.repositories.postgres.query_utils import (
    apply_filters,
    apply_pagination,
    apply_sort,
)
from cerebrum.repositories.soft_delete import SoftDeleteRepository
from cerebrum.utils.clock import utcnow


class FolderRepository(
    AbstractRepository[Folder, uuid.UUID], SoftDeleteRepository[Folder, uuid.UUID]
):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> Folder | None:
        """Never returns a soft-deleted folder — see
        :meth:`get_by_id_including_deleted` for the one internal caller
        (:meth:`restore`) that needs to see one.
        """
        folder = await self._session.get(Folder, entity_id)
        return None if folder is None or folder.is_deleted else folder

    async def get_by_id_including_deleted(self, entity_id: uuid.UUID) -> Folder | None:
        return await self._session.get(Folder, entity_id)

    async def get_by_name(
        self,
        *,
        workspace_id: uuid.UUID,
        parent_id: uuid.UUID | None,
        name: str,
    ) -> Folder | None:
        """Backs duplicate-name validation — see
        cerebrum.application.knowledge.folder_service.FolderService.
        """
        statement = select(Folder).where(
            Folder.workspace_id == workspace_id,
            Folder.parent_id == parent_id,
            Folder.name == name,
            Folder.is_deleted.is_(False),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_children(
        self, parent_id: uuid.UUID | None, *, workspace_id: uuid.UUID
    ) -> list[Folder]:
        """Every direct child of ``parent_id`` (``None`` = workspace
        root), unpaginated — used by
        cerebrum.application.knowledge.folder_service's descendant check
        (a folder tree is expected to be shallow/small; a workspace with
        thousands of direct children in one folder would need a
        paginated variant, Deferred until that's an actual problem).
        """
        statement = select(Folder).where(
            Folder.workspace_id == workspace_id,
            Folder.parent_id == parent_id,
            Folder.is_deleted.is_(False),
        )
        result = await self._session.execute(statement)
        return list(result.scalars())

    async def add(self, entity: Folder) -> Folder:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: Folder) -> Folder:
        await self._session.flush()
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        folder = await self.get_by_id_including_deleted(entity_id)
        if folder is not None:
            await self._session.delete(folder)
            await self._session.flush()

    async def soft_delete(self, entity_id: uuid.UUID) -> None:
        folder = await self.get_by_id_including_deleted(entity_id)
        if folder is not None:
            folder.is_deleted = True
            folder.deleted_at = utcnow()
            await self._session.flush()

    async def restore(self, entity_id: uuid.UUID) -> None:
        folder = await self.get_by_id_including_deleted(entity_id)
        if folder is not None:
            folder.is_deleted = False
            folder.deleted_at = None
            await self._session.flush()

    async def list(
        self,
        *,
        pagination: Pagination,
        filters: list[FilterSpec] | None = None,
        sort: list[SortSpec] | None = None,
    ) -> Page[Folder]:
        base_statement = apply_filters(select(Folder), Folder, filters).where(
            Folder.is_deleted.is_(False)
        )

        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = apply_sort(base_statement, Folder, sort)
        statement = apply_pagination(statement, pagination)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)
