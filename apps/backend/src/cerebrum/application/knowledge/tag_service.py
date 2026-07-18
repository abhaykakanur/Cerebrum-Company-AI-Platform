"""``TagService``: CRUD over
:class:`~cerebrum.infrastructure.database.models.tag.Tag` — assignment/
removal on a specific document lives in
cerebrum.application.knowledge.document_service.DocumentService, which
also owns the "does this tag belong to this workspace" check at
assignment time.
"""

import uuid

from cerebrum.infrastructure.database.models.tag import Tag
from cerebrum.repositories.contracts import (
    FilterOperator,
    FilterSpec,
    Page,
    Pagination,
    SortSpec,
)
from cerebrum.repositories.postgres.tag_repository import TagRepository
from cerebrum.shared.errors.exceptions import ConflictException, NotFoundException


class TagService:
    def __init__(self, tag_repository: TagRepository) -> None:
        self._tags = tag_repository

    async def create(self, *, workspace_id: uuid.UUID, name: str) -> Tag:
        existing = await self._tags.get_by_name(workspace_id=workspace_id, name=name)
        if existing is not None:
            raise ConflictException(f"A tag named '{name}' already exists.")
        return await self._tags.add(Tag(workspace_id=workspace_id, name=name))

    async def get(self, tag_id: uuid.UUID, *, workspace_id: uuid.UUID) -> Tag:
        tag = await self._tags.get_by_id(tag_id)
        if tag is None or tag.workspace_id != workspace_id:
            raise NotFoundException(f"No tag with id {tag_id}.")
        return tag

    async def rename(
        self, tag_id: uuid.UUID, *, workspace_id: uuid.UUID, name: str
    ) -> Tag:
        tag = await self.get(tag_id, workspace_id=workspace_id)
        existing = await self._tags.get_by_name(workspace_id=workspace_id, name=name)
        if existing is not None and existing.id != tag.id:
            raise ConflictException(f"A tag named '{name}' already exists.")
        tag.name = name
        return await self._tags.update(tag)

    async def delete(self, tag_id: uuid.UUID, *, workspace_id: uuid.UUID) -> None:
        await self.get(tag_id, workspace_id=workspace_id)
        await self._tags.delete(tag_id)

    async def list_in_workspace(
        self,
        *,
        workspace_id: uuid.UUID,
        pagination: Pagination,
        sort: list[SortSpec] | None = None,
    ) -> Page[Tag]:
        filters = [
            FilterSpec(
                field="workspace_id", operator=FilterOperator.EQ, value=workspace_id
            )
        ]
        return await self._tags.list(pagination=pagination, filters=filters, sort=sort)
