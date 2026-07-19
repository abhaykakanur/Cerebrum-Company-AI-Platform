"""``CapsuleRepository``: CRUD, soft delete/restore, and staleness
queries over
:class:`~cerebrum.infrastructure.database.models.capsule.EmployeeKnowledgeCapsule`
— CIS Phase 5 Prompt 3's Knowledge Capsule. Mirrors
cerebrum.repositories.postgres.workflow_repository.WorkflowRepository's
exact shape.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.capsule import EmployeeKnowledgeCapsule
from cerebrum.repositories.base import AbstractRepository
from cerebrum.repositories.contracts import FilterSpec, Page, Pagination, SortSpec
from cerebrum.repositories.postgres.query_utils import (
    apply_filters,
    apply_pagination,
    apply_sort,
)
from cerebrum.repositories.soft_delete import SoftDeleteRepository
from cerebrum.utils.clock import utcnow


class CapsuleRepository(
    AbstractRepository[EmployeeKnowledgeCapsule, uuid.UUID],
    SoftDeleteRepository[EmployeeKnowledgeCapsule, uuid.UUID],
):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> EmployeeKnowledgeCapsule | None:
        capsule = await self._session.get(EmployeeKnowledgeCapsule, entity_id)
        return None if capsule is None or capsule.is_deleted else capsule

    async def get_by_id_including_deleted(
        self, entity_id: uuid.UUID
    ) -> EmployeeKnowledgeCapsule | None:
        return await self._session.get(EmployeeKnowledgeCapsule, entity_id)

    async def get_by_user(
        self, user_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> EmployeeKnowledgeCapsule | None:
        statement = select(EmployeeKnowledgeCapsule).where(
            EmployeeKnowledgeCapsule.user_id == user_id,
            EmployeeKnowledgeCapsule.workspace_id == workspace_id,
            EmployeeKnowledgeCapsule.is_deleted.is_(False),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def add(self, entity: EmployeeKnowledgeCapsule) -> EmployeeKnowledgeCapsule:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(
        self, entity: EmployeeKnowledgeCapsule
    ) -> EmployeeKnowledgeCapsule:
        await self._session.flush()
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        capsule = await self._session.get(EmployeeKnowledgeCapsule, entity_id)
        if capsule is not None:
            await self._session.delete(capsule)
            await self._session.flush()

    async def soft_delete(self, entity_id: uuid.UUID) -> None:
        capsule = await self._session.get(EmployeeKnowledgeCapsule, entity_id)
        if capsule is not None:
            capsule.is_deleted = True
            capsule.deleted_at = utcnow()
            await self._session.flush()

    async def restore(self, entity_id: uuid.UUID) -> None:
        capsule = await self._session.get(EmployeeKnowledgeCapsule, entity_id)
        if capsule is not None:
            capsule.is_deleted = False
            capsule.deleted_at = None
            await self._session.flush()

    async def list_stale(
        self, *, workspace_id: uuid.UUID
    ) -> list[EmployeeKnowledgeCapsule]:
        """Continuous Updates' due-query: every non-deleted, linked
        (``person_entity_id`` set — an unlinked capsule cannot be
        refreshed, see
        cerebrum.application.capsules.employee_knowledge_capsule_service.EmployeeKnowledgeCapsuleService.refresh)
        capsule flagged stale by
        cerebrum.application.capsules.continuous_updates. A query to
        poll, not a timer this codebase runs itself — the same
        "ConnectorScheduler"/"WorkflowScheduler" precedent.
        """
        statement = select(EmployeeKnowledgeCapsule).where(
            EmployeeKnowledgeCapsule.workspace_id == workspace_id,
            EmployeeKnowledgeCapsule.is_deleted.is_(False),
            EmployeeKnowledgeCapsule.is_stale.is_(True),
            EmployeeKnowledgeCapsule.person_entity_id.is_not(None),
        )
        result = await self._session.execute(statement)
        return list(result.scalars())

    async def list(
        self,
        *,
        pagination: Pagination,
        filters: list[FilterSpec] | None = None,
        sort: list[SortSpec] | None = None,
    ) -> Page[EmployeeKnowledgeCapsule]:
        base_statement = apply_filters(
            select(EmployeeKnowledgeCapsule), EmployeeKnowledgeCapsule, filters
        ).where(EmployeeKnowledgeCapsule.is_deleted.is_(False))

        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = apply_sort(base_statement, EmployeeKnowledgeCapsule, sort)
        statement = apply_pagination(statement, pagination)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)
