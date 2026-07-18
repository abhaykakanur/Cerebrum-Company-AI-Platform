"""``DocumentRepository``: CRUD, soft delete/restore, and tag/label/
checksum queries over
:class:`~cerebrum.infrastructure.database.models.document.Document` —
CIS Phase 2 Prompt 1's central business entity.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.document import Document
from cerebrum.infrastructure.database.models.document_metadata import (
    DocumentMetadata,
)
from cerebrum.infrastructure.database.models.document_version import DocumentVersion
from cerebrum.infrastructure.database.models.label import DocumentLabel
from cerebrum.infrastructure.database.models.tag import DocumentTag
from cerebrum.repositories.base import AbstractRepository
from cerebrum.repositories.contracts import FilterSpec, Page, Pagination, SortSpec
from cerebrum.repositories.postgres.query_utils import (
    apply_filters,
    apply_pagination,
    apply_sort,
)
from cerebrum.repositories.soft_delete import SoftDeleteRepository
from cerebrum.utils.clock import utcnow


class DocumentRepository(
    AbstractRepository[Document, uuid.UUID], SoftDeleteRepository[Document, uuid.UUID]
):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> Document | None:
        document = await self._session.get(Document, entity_id)
        return None if document is None or document.is_deleted else document

    async def get_by_id_including_deleted(
        self, entity_id: uuid.UUID
    ) -> Document | None:
        return await self._session.get(Document, entity_id)

    async def get_by_name(
        self,
        *,
        workspace_id: uuid.UUID,
        folder_id: uuid.UUID | None,
        name: str,
    ) -> Document | None:
        """Backs duplicate-name validation — see
        cerebrum.application.knowledge.document_service.DocumentService.
        """
        statement = select(Document).where(
            Document.workspace_id == workspace_id,
            Document.folder_id == folder_id,
            Document.name == name,
            Document.is_deleted.is_(False),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def find_by_checksum(
        self, *, workspace_id: uuid.UUID, sha256_checksum: str
    ) -> Document | None:
        """Backs CIS Phase 2 Prompt 2's Duplicate Checksum validation —
        the first non-deleted document in this workspace whose *current*
        version's content hashes to ``sha256_checksum``, if any.
        """
        statement = (
            select(Document)
            .join(DocumentVersion, DocumentVersion.id == Document.current_version_id)
            .join(
                DocumentMetadata,
                DocumentMetadata.document_version_id == DocumentVersion.id,
            )
            .where(
                Document.workspace_id == workspace_id,
                Document.is_deleted.is_(False),
                DocumentMetadata.sha256_checksum == sha256_checksum,
            )
        )
        result = await self._session.execute(statement)
        return result.scalars().first()

    async def add(self, entity: Document) -> Document:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: Document) -> Document:
        await self._session.flush()
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        document = await self.get_by_id_including_deleted(entity_id)
        if document is not None:
            await self._session.delete(document)
            await self._session.flush()

    async def soft_delete(self, entity_id: uuid.UUID) -> None:
        document = await self.get_by_id_including_deleted(entity_id)
        if document is not None:
            document.is_deleted = True
            document.deleted_at = utcnow()
            await self._session.flush()

    async def restore(self, entity_id: uuid.UUID) -> None:
        document = await self.get_by_id_including_deleted(entity_id)
        if document is not None:
            document.is_deleted = False
            document.deleted_at = None
            await self._session.flush()

    async def add_tag(self, *, document_id: uuid.UUID, tag_id: uuid.UUID) -> None:
        exists = await self._session.get(DocumentTag, (document_id, tag_id))
        if exists is None:
            self._session.add(DocumentTag(document_id=document_id, tag_id=tag_id))
            await self._session.flush()

    async def remove_tag(self, *, document_id: uuid.UUID, tag_id: uuid.UUID) -> None:
        link = await self._session.get(DocumentTag, (document_id, tag_id))
        if link is not None:
            await self._session.delete(link)
            await self._session.flush()

    async def add_label(self, *, document_id: uuid.UUID, label_id: uuid.UUID) -> None:
        exists = await self._session.get(DocumentLabel, (document_id, label_id))
        if exists is None:
            self._session.add(DocumentLabel(document_id=document_id, label_id=label_id))
            await self._session.flush()

    async def remove_label(
        self, *, document_id: uuid.UUID, label_id: uuid.UUID
    ) -> None:
        link = await self._session.get(DocumentLabel, (document_id, label_id))
        if link is not None:
            await self._session.delete(link)
            await self._session.flush()

    async def list(
        self,
        *,
        pagination: Pagination,
        filters: list[FilterSpec] | None = None,
        sort: list[SortSpec] | None = None,
    ) -> Page[Document]:
        base_statement = apply_filters(select(Document), Document, filters).where(
            Document.is_deleted.is_(False)
        )

        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = apply_sort(base_statement, Document, sort)
        statement = apply_pagination(statement, pagination)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)
