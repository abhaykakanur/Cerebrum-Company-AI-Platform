"""``DocumentService``: CRUD, move, soft delete/restore, and tag/label
assignment over
:class:`~cerebrum.infrastructure.database.models.document.Document` —
CIS Phase 2 Prompt 1's central business entity. Version creation lives
in cerebrum.application.knowledge.version_service, not here — a
Document may exist (in ``Draft`` status) with zero versions.
"""

import uuid

from cerebrum.infrastructure.database.models.document import Document, DocumentStatus
from cerebrum.repositories.contracts import (
    FilterOperator,
    FilterSpec,
    Page,
    Pagination,
    SortSpec,
)
from cerebrum.repositories.postgres.document_repository import DocumentRepository
from cerebrum.repositories.postgres.folder_repository import FolderRepository
from cerebrum.repositories.postgres.label_repository import LabelRepository
from cerebrum.repositories.postgres.tag_repository import TagRepository
from cerebrum.shared.errors.exceptions import ConflictException, NotFoundException


class DocumentService:
    def __init__(
        self,
        *,
        document_repository: DocumentRepository,
        folder_repository: FolderRepository,
        tag_repository: TagRepository,
        label_repository: LabelRepository,
    ) -> None:
        self._documents = document_repository
        self._folders = folder_repository
        self._tags = tag_repository
        self._labels = label_repository

    async def create(
        self,
        *,
        workspace_id: uuid.UUID,
        folder_id: uuid.UUID | None,
        name: str,
        created_by: uuid.UUID,
    ) -> Document:
        if folder_id is not None:
            await self._require_folder_in_workspace(
                folder_id, workspace_id=workspace_id
            )
        await self._reject_duplicate_name(
            workspace_id=workspace_id, folder_id=folder_id, name=name
        )
        document = Document(
            workspace_id=workspace_id,
            folder_id=folder_id,
            name=name,
            status=DocumentStatus.DRAFT.value,
            created_by=created_by,
            updated_by=created_by,
        )
        return await self._documents.add(document)

    async def get(self, document_id: uuid.UUID, *, workspace_id: uuid.UUID) -> Document:
        document = await self._documents.get_by_id(document_id)
        if document is None or document.workspace_id != workspace_id:
            raise NotFoundException(f"No document with id {document_id}.")
        return document

    async def rename(
        self,
        document_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        name: str,
        updated_by: uuid.UUID,
    ) -> Document:
        document = await self.get(document_id, workspace_id=workspace_id)
        await self._reject_duplicate_name(
            workspace_id=workspace_id,
            folder_id=document.folder_id,
            name=name,
            exclude_id=document.id,
        )
        document.name = name
        document.updated_by = updated_by
        return await self._documents.update(document)

    async def move(
        self,
        document_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        new_folder_id: uuid.UUID | None,
        updated_by: uuid.UUID,
    ) -> Document:
        document = await self.get(document_id, workspace_id=workspace_id)
        if new_folder_id is not None:
            await self._require_folder_in_workspace(
                new_folder_id, workspace_id=workspace_id
            )
        await self._reject_duplicate_name(
            workspace_id=workspace_id,
            folder_id=new_folder_id,
            name=document.name,
            exclude_id=document.id,
        )
        document.folder_id = new_folder_id
        document.updated_by = updated_by
        return await self._documents.update(document)

    async def change_status(
        self,
        document_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        status: DocumentStatus,
        updated_by: uuid.UUID,
    ) -> Document:
        document = await self.get(document_id, workspace_id=workspace_id)
        document.status = status.value
        document.updated_by = updated_by
        return await self._documents.update(document)

    async def soft_delete(
        self, document_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> None:
        await self.get(document_id, workspace_id=workspace_id)
        await self._documents.soft_delete(document_id)

    async def restore(
        self, document_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> Document:
        document = await self._documents.get_by_id_including_deleted(document_id)
        if document is None or document.workspace_id != workspace_id:
            raise NotFoundException(f"No document with id {document_id}.")
        await self._documents.restore(document_id)
        restored = await self._documents.get_by_id(document_id)
        assert restored is not None
        return restored

    async def assign_tag(
        self, document_id: uuid.UUID, tag_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> None:
        document = await self.get(document_id, workspace_id=workspace_id)
        tag = await self._tags.get_by_id(tag_id)
        if tag is None or tag.workspace_id != workspace_id:
            raise NotFoundException(f"No tag with id {tag_id}.")
        await self._documents.add_tag(document_id=document.id, tag_id=tag.id)

    async def remove_tag(
        self, document_id: uuid.UUID, tag_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> None:
        await self.get(document_id, workspace_id=workspace_id)
        await self._documents.remove_tag(document_id=document_id, tag_id=tag_id)

    async def assign_label(
        self, document_id: uuid.UUID, label_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> None:
        document = await self.get(document_id, workspace_id=workspace_id)
        label = await self._labels.get_by_id(label_id)
        if label is None or label.workspace_id != workspace_id:
            raise NotFoundException(f"No label with id {label_id}.")
        await self._documents.add_label(document_id=document.id, label_id=label.id)

    async def remove_label(
        self, document_id: uuid.UUID, label_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> None:
        await self.get(document_id, workspace_id=workspace_id)
        await self._documents.remove_label(document_id=document_id, label_id=label_id)

    async def list_in_workspace(
        self,
        *,
        workspace_id: uuid.UUID,
        pagination: Pagination,
        filters: list[FilterSpec] | None = None,
        sort: list[SortSpec] | None = None,
    ) -> Page[Document]:
        scoped_filters = [
            FilterSpec(
                field="workspace_id", operator=FilterOperator.EQ, value=workspace_id
            ),
            *(filters or []),
        ]
        return await self._documents.list(
            pagination=pagination, filters=scoped_filters, sort=sort
        )

    async def _require_folder_in_workspace(
        self, folder_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> None:
        folder = await self._folders.get_by_id(folder_id)
        if folder is None or folder.workspace_id != workspace_id:
            raise NotFoundException(f"No folder with id {folder_id}.")

    async def _reject_duplicate_name(
        self,
        *,
        workspace_id: uuid.UUID,
        folder_id: uuid.UUID | None,
        name: str,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        existing = await self._documents.get_by_name(
            workspace_id=workspace_id, folder_id=folder_id, name=name
        )
        if existing is not None and existing.id != exclude_id:
            raise ConflictException(
                f"A document named '{name}' already exists in this location."
            )
