"""``FolderService``: hierarchy-aware CRUD, move, rename, soft delete,
and restore over
:class:`~cerebrum.infrastructure.database.models.folder.Folder` — CIS
Phase 2 Prompt 1's Folder System.
"""

import uuid

from cerebrum.infrastructure.database.models.folder import Folder
from cerebrum.repositories.contracts import (
    FilterOperator,
    FilterSpec,
    Page,
    Pagination,
    SortSpec,
)
from cerebrum.repositories.postgres.folder_repository import FolderRepository
from cerebrum.shared.errors.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)


class FolderService:
    def __init__(self, folder_repository: FolderRepository) -> None:
        self._folders = folder_repository

    async def create(
        self,
        *,
        workspace_id: uuid.UUID,
        parent_id: uuid.UUID | None,
        name: str,
        created_by: uuid.UUID,
    ) -> Folder:
        if parent_id is not None:
            await self._require_parent_in_workspace(
                parent_id, workspace_id=workspace_id
            )
        await self._reject_duplicate_name(
            workspace_id=workspace_id, parent_id=parent_id, name=name
        )
        folder = Folder(
            workspace_id=workspace_id,
            parent_id=parent_id,
            name=name,
            created_by=created_by,
            updated_by=created_by,
        )
        return await self._folders.add(folder)

    async def get(self, folder_id: uuid.UUID, *, workspace_id: uuid.UUID) -> Folder:
        folder = await self._folders.get_by_id(folder_id)
        if folder is None or folder.workspace_id != workspace_id:
            raise NotFoundException(f"No folder with id {folder_id}.")
        return folder

    async def rename(
        self,
        folder_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        name: str,
        updated_by: uuid.UUID,
    ) -> Folder:
        folder = await self.get(folder_id, workspace_id=workspace_id)
        await self._reject_duplicate_name(
            workspace_id=workspace_id,
            parent_id=folder.parent_id,
            name=name,
            exclude_id=folder.id,
        )
        folder.name = name
        folder.updated_by = updated_by
        return await self._folders.update(folder)

    async def move(
        self,
        folder_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        new_parent_id: uuid.UUID | None,
        updated_by: uuid.UUID,
    ) -> Folder:
        """Moves ``folder_id`` under ``new_parent_id`` — CIS Phase 2
        Prompt 1's Folder Hierarchy validation: a folder may never be
        moved into itself or into one of its own descendants (that
        would disconnect the subtree from the tree entirely, an
        unrecoverable cycle).
        """
        folder = await self.get(folder_id, workspace_id=workspace_id)
        if new_parent_id is not None:
            if new_parent_id == folder.id:
                raise ValidationException("A folder cannot be moved into itself.")
            await self._require_parent_in_workspace(
                new_parent_id, workspace_id=workspace_id
            )
            await self._reject_descendant_target(
                folder.id, target_id=new_parent_id, workspace_id=workspace_id
            )
        await self._reject_duplicate_name(
            workspace_id=workspace_id,
            parent_id=new_parent_id,
            name=folder.name,
            exclude_id=folder.id,
        )
        folder.parent_id = new_parent_id
        folder.updated_by = updated_by
        return await self._folders.update(folder)

    async def soft_delete(
        self, folder_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> None:
        await self.get(folder_id, workspace_id=workspace_id)  # 404 if foreign/missing
        await self._folders.soft_delete(folder_id)

    async def restore(self, folder_id: uuid.UUID, *, workspace_id: uuid.UUID) -> Folder:
        folder = await self._folders.get_by_id_including_deleted(folder_id)
        if folder is None or folder.workspace_id != workspace_id:
            raise NotFoundException(f"No folder with id {folder_id}.")
        await self._folders.restore(folder_id)
        restored = await self._folders.get_by_id(folder_id)
        assert restored is not None
        return restored

    async def list_in_workspace(
        self,
        *,
        workspace_id: uuid.UUID,
        parent_id: uuid.UUID | None,
        pagination: Pagination,
        sort: list[SortSpec] | None = None,
    ) -> Page[Folder]:
        filters = [
            FilterSpec(
                field="workspace_id", operator=FilterOperator.EQ, value=workspace_id
            ),
            FilterSpec(field="parent_id", operator=FilterOperator.EQ, value=parent_id),
        ]
        return await self._folders.list(
            pagination=pagination, filters=filters, sort=sort
        )

    async def _require_parent_in_workspace(
        self, parent_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> None:
        parent = await self._folders.get_by_id(parent_id)
        if parent is None or parent.workspace_id != workspace_id:
            raise NotFoundException(f"No parent folder with id {parent_id}.")

    async def _reject_duplicate_name(
        self,
        *,
        workspace_id: uuid.UUID,
        parent_id: uuid.UUID | None,
        name: str,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        existing = await self._folders.get_by_name(
            workspace_id=workspace_id, parent_id=parent_id, name=name
        )
        if existing is not None and existing.id != exclude_id:
            raise ConflictException(
                f"A folder named '{name}' already exists in this location."
            )

    async def _reject_descendant_target(
        self, folder_id: uuid.UUID, *, target_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> None:
        """Walks up from ``target_id`` toward the workspace root; if
        ``folder_id`` appears on that path, ``target_id`` is a
        descendant of ``folder_id`` and the move would create a cycle.
        """
        current_id: uuid.UUID | None = target_id
        while current_id is not None:
            if current_id == folder_id:
                raise ValidationException(
                    "A folder cannot be moved into one of its own descendants."
                )
            current = await self._folders.get_by_id(current_id)
            current_id = current.parent_id if current is not None else None
