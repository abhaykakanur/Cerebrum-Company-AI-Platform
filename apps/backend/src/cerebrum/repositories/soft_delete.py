"""The soft-delete contract: an alternative to
:meth:`~cerebrum.repositories.base.AbstractRepository.delete`'s hard
delete for entities that must remain queryable (e.g., for audit or
recovery) after deletion.

A repository that supports soft delete implements both
:class:`~cerebrum.repositories.base.AbstractRepository` and
:class:`SoftDeleteRepository`; one that doesn't need soft delete
implements only the former. Kept as a separate, optional contract rather
than folded into the base CRUD contract so a repository that will never
soft-delete anything isn't forced to implement no-op
``restore``/``soft_delete`` methods.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class SoftDeletable(Protocol):
    """An entity that carries its own soft-delete state. A repository's
    concrete entity type satisfies this by declaring these two
    attributes/properties — no inheritance required.
    """

    is_deleted: bool
    deleted_at: datetime | None


class SoftDeleteRepository[EntityT, IDT](ABC):
    """Soft-delete and restore, generic over the same ``EntityT``/``IDT``
    pair a concrete repository's
    :class:`~cerebrum.repositories.base.AbstractRepository` is
    parameterized with (PEP 695 type parameters are declared per-class,
    not shared module-level symbols — the two independently-declared
    ``EntityT``/``IDT`` pairs unify correctly wherever a concrete class
    inherits both).
    """

    @abstractmethod
    async def soft_delete(self, entity_id: IDT) -> None:
        """Marks the entity deleted without removing its row/document —
        implementations set ``is_deleted=True`` and ``deleted_at=now()``
        (see :class:`SoftDeletable`) rather than issuing a hard delete.
        """
        ...

    @abstractmethod
    async def restore(self, entity_id: IDT) -> None:
        """Reverses :meth:`soft_delete`."""
        ...
