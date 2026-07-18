"""``CollectionService``: CRUD, soft delete/restore, and document
membership over
:class:`~cerebrum.infrastructure.database.models.collection.Collection`
— CIS Phase 2 Prompt 1's Collections. Bulk add/remove (CIS Phase 2
Prompt 2) is layered on top of the single-document
:meth:`add_document`/:meth:`remove_document` here, not a separate code
path.
"""

import uuid

from cerebrum.infrastructure.database.models.collection import Collection
from cerebrum.repositories.contracts import (
    FilterOperator,
    FilterSpec,
    Page,
    Pagination,
    SortSpec,
)
from cerebrum.repositories.postgres.collection_repository import CollectionRepository
from cerebrum.repositories.postgres.document_repository import DocumentRepository
from cerebrum.shared.errors.exceptions import ConflictException, NotFoundException


class CollectionService:
    def __init__(
        self,
        *,
        collection_repository: CollectionRepository,
        document_repository: DocumentRepository,
    ) -> None:
        self._collections = collection_repository
        self._documents = document_repository

    async def create(
        self,
        *,
        workspace_id: uuid.UUID,
        name: str,
        description: str | None,
        created_by: uuid.UUID,
    ) -> Collection:
        existing = await self._collections.get_by_name(
            workspace_id=workspace_id, name=name
        )
        if existing is not None:
            raise ConflictException(f"A collection named '{name}' already exists.")
        collection = Collection(
            workspace_id=workspace_id,
            name=name,
            description=description,
            created_by=created_by,
            updated_by=created_by,
        )
        return await self._collections.add(collection)

    async def get(
        self, collection_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> Collection:
        collection = await self._collections.get_by_id(collection_id)
        if collection is None or collection.workspace_id != workspace_id:
            raise NotFoundException(f"No collection with id {collection_id}.")
        return collection

    async def rename(
        self,
        collection_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        name: str,
        description: str | None,
        updated_by: uuid.UUID,
    ) -> Collection:
        collection = await self.get(collection_id, workspace_id=workspace_id)
        existing = await self._collections.get_by_name(
            workspace_id=workspace_id, name=name
        )
        if existing is not None and existing.id != collection.id:
            raise ConflictException(f"A collection named '{name}' already exists.")
        collection.name = name
        collection.description = description
        collection.updated_by = updated_by
        return await self._collections.update(collection)

    async def soft_delete(
        self, collection_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> None:
        await self.get(collection_id, workspace_id=workspace_id)
        await self._collections.soft_delete(collection_id)

    async def restore(
        self, collection_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> Collection:
        collection = await self._collections.get_by_id_including_deleted(collection_id)
        if collection is None or collection.workspace_id != workspace_id:
            raise NotFoundException(f"No collection with id {collection_id}.")
        await self._collections.restore(collection_id)
        restored = await self._collections.get_by_id(collection_id)
        assert restored is not None
        return restored

    async def add_document(
        self,
        collection_id: uuid.UUID,
        document_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
    ) -> None:
        collection = await self.get(collection_id, workspace_id=workspace_id)
        document = await self._documents.get_by_id(document_id)
        if document is None or document.workspace_id != workspace_id:
            raise NotFoundException(f"No document with id {document_id}.")
        await self._collections.add_document(
            collection_id=collection.id, document_id=document.id
        )

    async def remove_document(
        self,
        collection_id: uuid.UUID,
        document_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
    ) -> None:
        await self.get(collection_id, workspace_id=workspace_id)
        await self._collections.remove_document(
            collection_id=collection_id, document_id=document_id
        )

    async def add_documents_bulk(
        self,
        collection_id: uuid.UUID,
        document_ids: list[uuid.UUID],
        *,
        workspace_id: uuid.UUID,
    ) -> int:
        """CIS Phase 2 Prompt 2's Bulk Operations. Returns the number of
        documents actually added — an ID that doesn't resolve to a
        document in this workspace is silently skipped, not a hard
        failure of the whole batch (a partial success is more useful to
        a caller than losing every valid addition because one ID in a
        hundred was wrong).
        """
        await self.get(collection_id, workspace_id=workspace_id)
        added = 0
        for document_id in document_ids:
            document = await self._documents.get_by_id(document_id)
            if document is not None and document.workspace_id == workspace_id:
                await self._collections.add_document(
                    collection_id=collection_id, document_id=document_id
                )
                added += 1
        return added

    async def remove_documents_bulk(
        self,
        collection_id: uuid.UUID,
        document_ids: list[uuid.UUID],
        *,
        workspace_id: uuid.UUID,
    ) -> None:
        await self.get(collection_id, workspace_id=workspace_id)
        for document_id in document_ids:
            await self._collections.remove_document(
                collection_id=collection_id, document_id=document_id
            )

    async def list_documents(
        self,
        collection_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        pagination: Pagination,
    ) -> Page[uuid.UUID]:
        await self.get(collection_id, workspace_id=workspace_id)
        return await self._collections.list_document_ids(
            collection_id, pagination=pagination
        )

    async def list_in_workspace(
        self,
        *,
        workspace_id: uuid.UUID,
        pagination: Pagination,
        sort: list[SortSpec] | None = None,
    ) -> Page[Collection]:
        filters = [
            FilterSpec(
                field="workspace_id", operator=FilterOperator.EQ, value=workspace_id
            )
        ]
        return await self._collections.list(
            pagination=pagination, filters=filters, sort=sort
        )
