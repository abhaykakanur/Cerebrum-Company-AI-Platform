"""``WorkflowVersionRepository``: CRUD and version-sequencing queries
over
:class:`~cerebrum.infrastructure.database.models.workflow_version.WorkflowVersion`
— CIS Phase 5 Prompt 2's Workflow Versioning. Mirrors
cerebrum.repositories.postgres.document_version_repository.DocumentVersionRepository's
shape; no ``is_current`` flag exists here (see
cerebrum.infrastructure.database.models.workflow_version's docstring
— :attr:`~cerebrum.infrastructure.database.models.workflow.Workflow.current_version_id`
alone is the single source of truth), so there is no analogous
``unset_current``.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.workflow_version import WorkflowVersion
from cerebrum.repositories.contracts import Page, Pagination


class WorkflowVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> WorkflowVersion | None:
        return await self._session.get(WorkflowVersion, entity_id)

    async def get_by_number(
        self, workflow_id: uuid.UUID, version_number: int
    ) -> WorkflowVersion | None:
        statement = select(WorkflowVersion).where(
            WorkflowVersion.workflow_id == workflow_id,
            WorkflowVersion.version_number == version_number,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_next_version_number(self, workflow_id: uuid.UUID) -> int:
        """A strictly incrementing sequence per workflow, computed from
        the current ``max(version_number)`` — the same
        self-healing-under-deletion reasoning
        cerebrum.repositories.postgres.document_version_repository.DocumentVersionRepository.get_next_version_number
        documents (workflow versions are never deleted in practice, but
        the computation carries no such assumption).
        """
        statement = select(func.max(WorkflowVersion.version_number)).where(
            WorkflowVersion.workflow_id == workflow_id
        )
        current_max = (await self._session.execute(statement)).scalar_one()
        return (current_max or 0) + 1

    async def add(self, entity: WorkflowVersion) -> WorkflowVersion:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def list_by_workflow(
        self, workflow_id: uuid.UUID, *, pagination: Pagination
    ) -> Page[WorkflowVersion]:
        base_statement = select(WorkflowVersion).where(
            WorkflowVersion.workflow_id == workflow_id
        )
        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = base_statement.order_by(WorkflowVersion.version_number.desc())
        statement = statement.offset(pagination.offset).limit(pagination.page_size)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)
