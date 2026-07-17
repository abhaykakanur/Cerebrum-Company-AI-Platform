"""The Queue interface — a background job queue's contract, independent
of the concrete broker (Redis-backed Celery, per
docs/architecture/specification/32_Technology_Stack.md) that will
implement it in infrastructure/ in a future phase.
"""

from abc import ABC, abstractmethod

from cerebrum.workers.base import Job


class Queue[PayloadT](ABC):
    """A FIFO job queue contract."""

    @abstractmethod
    async def enqueue(self, job: Job[PayloadT]) -> None: ...

    @abstractmethod
    async def dequeue(self) -> Job[PayloadT] | None: ...

    @abstractmethod
    async def size(self) -> int: ...
