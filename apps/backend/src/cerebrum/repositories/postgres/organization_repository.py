"""``OrganizationRepository``: CIS Phase 2 Prompt 1's first concrete
CRUD surface over
:class:`~cerebrum.infrastructure.database.models.organization.Organization`
— the model itself has existed since CIS Phase 1 Prompt 5, but only as
the tenant-isolation boundary the Identity & Security platform reads,
never as a business-CRUD target. No ``delete()``: an organization is the
tenant root — deleting one is Deferred to Architecture (a future
platform-admin operation with cascading-deletion implications well
beyond this domain's scope), so this repository deliberately does not
implement :class:`~cerebrum.repositories.soft_delete.SoftDeleteRepository`
either.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.organization import Organization
from cerebrum.repositories.base import AbstractRepository
from cerebrum.repositories.contracts import FilterSpec, Page, Pagination, SortSpec
from cerebrum.repositories.postgres.query_utils import (
    apply_filters,
    apply_pagination,
    apply_sort,
)
from cerebrum.shared.errors.exceptions import ValidationException


class OrganizationRepository(AbstractRepository[Organization, uuid.UUID]):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> Organization | None:
        return await self._session.get(Organization, entity_id)

    async def get_by_slug(self, slug: str) -> Organization | None:
        result = await self._session.execute(
            select(Organization).where(Organization.slug == slug)
        )
        return result.scalar_one_or_none()

    async def add(self, entity: Organization) -> Organization:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: Organization) -> Organization:
        await self._session.flush()
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        raise ValidationException(
            "Organizations cannot be deleted through this repository — see "
            "this module's docstring."
        )

    async def list(
        self,
        *,
        pagination: Pagination,
        filters: list[FilterSpec] | None = None,
        sort: list[SortSpec] | None = None,
    ) -> Page[Organization]:
        base_statement = apply_filters(select(Organization), Organization, filters)

        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = apply_sort(base_statement, Organization, sort)
        statement = apply_pagination(statement, pagination)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)
