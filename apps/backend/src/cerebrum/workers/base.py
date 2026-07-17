"""Background execution framework — interfaces only, per CIS Phase 1
Prompt 3 Section 1's Background Foundation requirement ("No concrete
implementations"). The nine named Workers
(docs/architecture/specification/36_Background_Processing.md) each
implement :class:`Worker` in a future phase; none exist yet.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from cerebrum.utils.clock import utcnow


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"


class WorkerStatus(StrEnum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"


@dataclass(frozen=True, slots=True, kw_only=True)
class Job[PayloadT]:
    """A unit of background work. Concrete job payloads (connector sync,
    OCR, embedding, ...) are defined alongside the Worker that consumes
    them, in a future phase.
    """

    payload: PayloadT
    job_id: UUID = field(default_factory=uuid4)
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=utcnow)


class Worker[PayloadT](ABC):
    """The contract every concrete background worker implements. Owns no
    business rules of its own — see cerebrum.workers's package docstring
    ("Workers orchestrate calls into domain/application services; they
    contain no business rules of their own").
    """

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def status(self) -> WorkerStatus: ...

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    async def process(self, job: Job[PayloadT]) -> None: ...
