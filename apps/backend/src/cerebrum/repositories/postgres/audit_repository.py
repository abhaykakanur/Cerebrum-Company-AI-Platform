"""``AuditEventRepository``: append-only audit trail storage.

``update()`` and ``delete()`` are implemented —
:class:`~cerebrum.repositories.base.AbstractRepository` requires them —
but both deliberately raise rather than silently
succeed: an audit record is immutable and non-deletable once written,
per docs/architecture/specification/38_Observability.md ("a distinct,
append-only, non-deletable stream"). Rejecting the call explicitly, with
a clear reason, is safer than a method a future caller could reasonably
assume works.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.audit import AuditEvent
from cerebrum.repositories.base import AbstractRepository
from cerebrum.repositories.contracts import FilterSpec, Page, Pagination, SortSpec
from cerebrum.repositories.postgres.query_utils import (
    apply_filters,
    apply_pagination,
    apply_sort,
)
from cerebrum.shared.errors.exceptions import ValidationException


class AuditEventRepository(AbstractRepository[AuditEvent, uuid.UUID]):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> AuditEvent | None:
        return await self._session.get(AuditEvent, entity_id)

    async def add(self, entity: AuditEvent) -> AuditEvent:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: AuditEvent) -> AuditEvent:
        raise ValidationException("Audit events are append-only and cannot be updated.")

    async def delete(self, entity_id: uuid.UUID) -> None:
        raise ValidationException("Audit events are append-only and cannot be deleted.")

    async def list(
        self,
        *,
        pagination: Pagination,
        filters: list[FilterSpec] | None = None,
        sort: list[SortSpec] | None = None,
    ) -> Page[AuditEvent]:
        base_statement = apply_filters(select(AuditEvent), AuditEvent, filters)

        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = apply_sort(base_statement, AuditEvent, sort)
        statement = apply_pagination(statement, pagination)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)
