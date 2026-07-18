"""``ProcessingJobRepository``: CRUD over
:class:`~cerebrum.infrastructure.database.models.processing_job.ProcessingJob`
— CIS Phase 2 Prompt 2's Background Processing framework persistence.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.processing_job import ProcessingJob
from cerebrum.repositories.base import AbstractRepository
from cerebrum.repositories.contracts import FilterSpec, Page, Pagination, SortSpec
from cerebrum.repositories.postgres.query_utils import (
    apply_filters,
    apply_pagination,
    apply_sort,
)


class ProcessingJobRepository(AbstractRepository[ProcessingJob, uuid.UUID]):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> ProcessingJob | None:
        return await self._session.get(ProcessingJob, entity_id)

    async def list_by_document_version(
        self, document_version_id: uuid.UUID
    ) -> list[ProcessingJob]:
        result = await self._session.execute(
            select(ProcessingJob).where(
                ProcessingJob.document_version_id == document_version_id
            )
        )
        return list(result.scalars())

    async def add(self, entity: ProcessingJob) -> ProcessingJob:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: ProcessingJob) -> ProcessingJob:
        await self._session.flush()
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        job = await self.get_by_id(entity_id)
        if job is not None:
            await self._session.delete(job)
            await self._session.flush()

    async def list(
        self,
        *,
        pagination: Pagination,
        filters: list[FilterSpec] | None = None,
        sort: list[SortSpec] | None = None,
    ) -> Page[ProcessingJob]:
        base_statement = apply_filters(select(ProcessingJob), ProcessingJob, filters)

        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = apply_sort(base_statement, ProcessingJob, sort)
        statement = apply_pagination(statement, pagination)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)
