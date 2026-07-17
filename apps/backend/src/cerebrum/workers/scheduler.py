"""The Scheduler interface — recurring/deferred background work,
independent of the concrete implementation (e.g. Celery Beat) a future
infrastructure adapter provides.
"""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from datetime import datetime


class Scheduler(ABC):
    """Schedules a callable to run once at a future time, or on a
    recurring interval. No concrete schedule is registered anywhere yet.
    """

    @abstractmethod
    async def schedule_once(
        self, run_at: datetime, callback: Callable[[], Awaitable[None]]
    ) -> str:
        """Returns a schedule ID that can later be passed to :meth:`cancel`."""
        ...

    @abstractmethod
    async def schedule_interval(
        self, interval_seconds: float, callback: Callable[[], Awaitable[None]]
    ) -> str:
        """Returns a schedule ID that can later be passed to :meth:`cancel`."""
        ...

    @abstractmethod
    async def cancel(self, schedule_id: str) -> None: ...
