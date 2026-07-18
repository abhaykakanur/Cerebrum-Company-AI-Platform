"""``DocumentVersionRepository``: CRUD and version-sequencing queries
over
:class:`~cerebrum.infrastructure.database.models.document_version.DocumentVersion`
— CIS Phase 2 Prompt 1's Versioning requirement. No soft delete (see
that model's own docstring for why); ``delete()`` is a hard delete, used
only for the (rare, RBAC-gated) permanent removal of a specific version.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.document_version import DocumentVersion
from cerebrum.repositories.base import AbstractRepository
from cerebrum.repositories.contracts import FilterSpec, Page, Pagination, SortSpec
from cerebrum.repositories.postgres.query_utils import (
    apply_filters,
    apply_pagination,
    apply_sort,
)


class DocumentVersionRepository(AbstractRepository[DocumentVersion, uuid.UUID]):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> DocumentVersion | None:
        return await self._session.get(DocumentVersion, entity_id)

    async def get_current(self, document_id: uuid.UUID) -> DocumentVersion | None:
        statement = select(DocumentVersion).where(
            DocumentVersion.document_id == document_id,
            DocumentVersion.is_current.is_(True),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_next_version_number(self, document_id: uuid.UUID) -> int:
        """Backs version-consistency validation — a strictly incrementing
        sequence per document, computed from the current
        ``max(version_number)`` rather than a separately-tracked counter
        column, so it self-heals if a version is ever hard-deleted.
        """
        statement = select(func.max(DocumentVersion.version_number)).where(
            DocumentVersion.document_id == document_id
        )
        current_max = (await self._session.execute(statement)).scalar_one()
        return (current_max or 0) + 1

    async def list_by_document(
        self, document_id: uuid.UUID, *, pagination: Pagination
    ) -> Page[DocumentVersion]:
        base_statement = select(DocumentVersion).where(
            DocumentVersion.document_id == document_id
        )
        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = base_statement.order_by(DocumentVersion.version_number.desc())
        statement = apply_pagination(statement, pagination)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)

    async def unset_current(self, document_id: uuid.UUID) -> None:
        """Clears ``is_current`` on every version of ``document_id`` —
        called immediately before marking a (possibly different) version
        current, so exactly one version is ever current at a time. See
        cerebrum.application.knowledge.version_service.
        """
        current = await self.get_current(document_id)
        if current is not None:
            current.is_current = False
            await self._session.flush()

    async def add(self, entity: DocumentVersion) -> DocumentVersion:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: DocumentVersion) -> DocumentVersion:
        await self._session.flush()
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        version = await self.get_by_id(entity_id)
        if version is not None:
            await self._session.delete(version)
            await self._session.flush()

    async def list(
        self,
        *,
        pagination: Pagination,
        filters: list[FilterSpec] | None = None,
        sort: list[SortSpec] | None = None,
    ) -> Page[DocumentVersion]:
        base_statement = apply_filters(
            select(DocumentVersion), DocumentVersion, filters
        )

        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = apply_sort(base_statement, DocumentVersion, sort)
        statement = apply_pagination(statement, pagination)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)
