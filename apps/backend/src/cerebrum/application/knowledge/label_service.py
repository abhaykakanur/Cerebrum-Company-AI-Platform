"""``LabelService``: CRUD over
:class:`~cerebrum.infrastructure.database.models.label.Label` — see
cerebrum.application.knowledge.tag_service's docstring; identical shape.
"""

import uuid

from cerebrum.infrastructure.database.models.label import Label
from cerebrum.repositories.contracts import (
    FilterOperator,
    FilterSpec,
    Page,
    Pagination,
    SortSpec,
)
from cerebrum.repositories.postgres.label_repository import LabelRepository
from cerebrum.shared.errors.exceptions import ConflictException, NotFoundException


class LabelService:
    def __init__(self, label_repository: LabelRepository) -> None:
        self._labels = label_repository

    async def create(
        self, *, workspace_id: uuid.UUID, name: str, color: str | None = None
    ) -> Label:
        existing = await self._labels.get_by_name(workspace_id=workspace_id, name=name)
        if existing is not None:
            raise ConflictException(f"A label named '{name}' already exists.")
        return await self._labels.add(
            Label(workspace_id=workspace_id, name=name, color=color)
        )

    async def get(self, label_id: uuid.UUID, *, workspace_id: uuid.UUID) -> Label:
        label = await self._labels.get_by_id(label_id)
        if label is None or label.workspace_id != workspace_id:
            raise NotFoundException(f"No label with id {label_id}.")
        return label

    async def rename(
        self,
        label_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        name: str,
        color: str | None = None,
    ) -> Label:
        label = await self.get(label_id, workspace_id=workspace_id)
        existing = await self._labels.get_by_name(workspace_id=workspace_id, name=name)
        if existing is not None and existing.id != label.id:
            raise ConflictException(f"A label named '{name}' already exists.")
        label.name = name
        if color is not None:
            label.color = color
        return await self._labels.update(label)

    async def delete(self, label_id: uuid.UUID, *, workspace_id: uuid.UUID) -> None:
        await self.get(label_id, workspace_id=workspace_id)
        await self._labels.delete(label_id)

    async def list_in_workspace(
        self,
        *,
        workspace_id: uuid.UUID,
        pagination: Pagination,
        sort: list[SortSpec] | None = None,
    ) -> Page[Label]:
        filters = [
            FilterSpec(
                field="workspace_id", operator=FilterOperator.EQ, value=workspace_id
            )
        ]
        return await self._labels.list(
            pagination=pagination, filters=filters, sort=sort
        )
