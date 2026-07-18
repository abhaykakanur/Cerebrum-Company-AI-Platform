"""``OrganizationService``: read/rename operations on the caller's own
:class:`~cerebrum.infrastructure.database.models.organization.Organization`
— never an arbitrary one. Organization creation/deletion is a
platform-admin operation Deferred to Architecture (no such role exists
yet) — see cerebrum.repositories.postgres.organization_repository's
docstring for why ``delete()`` isn't exposed at all.
"""

import uuid

from cerebrum.infrastructure.database.models.organization import Organization
from cerebrum.repositories.postgres.organization_repository import (
    OrganizationRepository,
)
from cerebrum.shared.errors.exceptions import NotFoundException


class OrganizationService:
    def __init__(self, organization_repository: OrganizationRepository) -> None:
        self._organizations = organization_repository

    async def get(self, organization_id: uuid.UUID) -> Organization:
        organization = await self._organizations.get_by_id(organization_id)
        if organization is None:
            raise NotFoundException(f"No organization with id {organization_id}.")
        return organization

    async def rename(self, organization_id: uuid.UUID, *, name: str) -> Organization:
        organization = await self.get(organization_id)
        organization.name = name
        return await self._organizations.update(organization)
