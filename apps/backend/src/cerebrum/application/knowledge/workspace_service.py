"""``WorkspaceService``: CRUD over
:class:`~cerebrum.infrastructure.database.models.workspace.Workspace`
within the caller's own organization — CIS Phase 2 Prompt 1's Tenant
Ownership validation is structural here: every method takes
``organization_id`` from the caller's
:data:`~cerebrum.dependencies.request_context.TenantIdDep` (the access
token's claim, never client input — see
docs/architecture/security/multi-tenancy-guide.md), so a workspace
belonging to a different organization is simply never reachable through
this service, not filtered after the fact.
"""

import uuid

from cerebrum.infrastructure.database.models.workspace import Workspace
from cerebrum.repositories.contracts import (
    FilterOperator,
    FilterSpec,
    Page,
    Pagination,
    SortSpec,
)
from cerebrum.repositories.postgres.workspace_repository import WorkspaceRepository
from cerebrum.shared.errors.exceptions import ConflictException, NotFoundException


class WorkspaceService:
    def __init__(self, workspace_repository: WorkspaceRepository) -> None:
        self._workspaces = workspace_repository

    async def create(
        self, *, organization_id: uuid.UUID, name: str, slug: str
    ) -> Workspace:
        existing = await self._workspaces.get_by_slug(
            organization_id=organization_id, slug=slug
        )
        if existing is not None:
            raise ConflictException(
                f"A workspace with slug '{slug}' already exists in this organization."
            )
        workspace = Workspace(organization_id=organization_id, name=name, slug=slug)
        return await self._workspaces.add(workspace)

    async def get(
        self, workspace_id: uuid.UUID, *, organization_id: uuid.UUID
    ) -> Workspace:
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None or workspace.organization_id != organization_id:
            raise NotFoundException(f"No workspace with id {workspace_id}.")
        return workspace

    async def rename(
        self, workspace_id: uuid.UUID, *, organization_id: uuid.UUID, name: str
    ) -> Workspace:
        workspace = await self.get(workspace_id, organization_id=organization_id)
        workspace.name = name
        return await self._workspaces.update(workspace)

    async def delete(
        self, workspace_id: uuid.UUID, *, organization_id: uuid.UUID
    ) -> None:
        await self.get(workspace_id, organization_id=organization_id)  # 404 if foreign
        await self._workspaces.delete(workspace_id)

    async def list_for_organization(
        self,
        *,
        organization_id: uuid.UUID,
        pagination: Pagination,
        sort: list[SortSpec] | None = None,
    ) -> Page[Workspace]:
        filters = [
            FilterSpec(
                field="organization_id",
                operator=FilterOperator.EQ,
                value=organization_id,
            )
        ]
        return await self._workspaces.list(
            pagination=pagination, filters=filters, sort=sort
        )
