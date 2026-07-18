"""``RoleRepository``: role storage, plus the one specialized query the
RBAC permission check needs — the User → WorkspaceMembership → Role →
RolePermission → Permission join. See
docs/architecture/security/rbac-guide.md.

No separate ``PermissionRepository``/``WorkspaceMembershipRepository``
exists: CIS Phase 1 Prompt 5 asks for the RBAC *framework*, not a full
CRUD surface over every association table — see
cerebrum.application.auth.authorization_service, this repository's only
caller.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.membership import WorkspaceMembership
from cerebrum.infrastructure.database.models.role import (
    Permission,
    Role,
    RolePermission,
)
from cerebrum.repositories.base import AbstractRepository
from cerebrum.repositories.contracts import FilterSpec, Page, Pagination, SortSpec
from cerebrum.repositories.postgres.query_utils import (
    apply_filters,
    apply_pagination,
    apply_sort,
)


class RoleRepository(AbstractRepository[Role, uuid.UUID]):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> Role | None:
        return await self._session.get(Role, entity_id)

    async def get_permission_codes_for_membership(
        self, *, user_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> frozenset[str]:
        """Every permission code the given user holds in the given
        workspace, via their single
        :class:`~cerebrum.infrastructure.database.models.membership.WorkspaceMembership`
        row's role. Returns an empty set — not an error — for a user
        with no membership in that workspace; the caller
        (:class:`~cerebrum.application.auth.authorization_service.AuthorizationService`)
        is what turns "permission not in this set" into
        :class:`~cerebrum.shared.errors.exceptions.PermissionDeniedException`.
        """
        statement = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(WorkspaceMembership, WorkspaceMembership.role_id == Role.id)
            .where(
                WorkspaceMembership.user_id == user_id,
                WorkspaceMembership.workspace_id == workspace_id,
            )
        )
        result = await self._session.execute(statement)
        return frozenset(result.scalars())

    async def add(self, entity: Role) -> Role:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: Role) -> Role:
        await self._session.flush()
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        role = await self.get_by_id(entity_id)
        if role is not None:
            await self._session.delete(role)
            await self._session.flush()

    async def list(
        self,
        *,
        pagination: Pagination,
        filters: list[FilterSpec] | None = None,
        sort: list[SortSpec] | None = None,
    ) -> Page[Role]:
        base_statement = apply_filters(select(Role), Role, filters)

        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = apply_sort(base_statement, Role, sort)
        statement = apply_pagination(statement, pagination)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)
