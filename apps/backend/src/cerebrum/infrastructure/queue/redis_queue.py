"""``RedisQueue``: a Redis-list-backed FIFO implementation of
:class:`~cerebrum.workers.queue.Queue` — CIS Phase 2 Prompt 2's
Background Processing framework. Queues a
:class:`~cerebrum.workers.base.Job`'s ID only; the job's actual work
description lives in PostgreSQL (see
:class:`~cerebrum.infrastructure.database.models.processing_job.ProcessingJob`),
so a future worker dequeues an ID and loads full job details from
there, never trusting Redis as the durable record.

No worker consumes this queue yet — see
cerebrum.workers.base.Worker's docstring ("none exist yet") and this
milestone's explicit "Prepare jobs ... Do not implement them" scope.
This class makes ``enqueue``/``dequeue`` real and testable; a future
phase adds the ``Worker`` that actually calls ``dequeue`` in a loop.
"""

import json
import uuid
from datetime import datetime

from redis.asyncio import Redis

from cerebrum.workers.base import Job, JobStatus
from cerebrum.workers.queue import Queue

_DEFAULT_QUEUE_KEY = "cerebrum:queue:processing_jobs"


class RedisQueue(Queue[uuid.UUID]):
    def __init__(
        self, redis_client: Redis, *, queue_key: str = _DEFAULT_QUEUE_KEY
    ) -> None:
        self._redis = redis_client
        self._queue_key = queue_key

    async def enqueue(self, job: Job[uuid.UUID]) -> None:
        await self._redis.rpush(self._queue_key, self._serialize(job))

    async def dequeue(self) -> Job[uuid.UUID] | None:
        # redis-py's stub types LPOP's return as `str | bytes | list[...] |
        # None` to cover the `count=` overload, which returns a list; a
        # plain no-count call (this one) only ever returns a scalar or
        # None, never a list — the isinstance check is for mypy, not a
        # runtime case this method actually needs to handle.
        raw = await self._redis.lpop(self._queue_key)
        if raw is None:
            return None
        if isinstance(raw, list):
            raw = raw[0]
        return self._deserialize(raw)

    async def size(self) -> int:
        return await self._redis.llen(self._queue_key)

    @staticmethod
    def _serialize(job: Job[uuid.UUID]) -> str:
        return json.dumps(
            {
                "job_id": str(job.job_id),
                "payload": str(job.payload),
                "status": job.status.value,
                "created_at": job.created_at.isoformat(),
            }
        )

    @staticmethod
    def _deserialize(raw: str | bytes) -> Job[uuid.UUID]:
        data = json.loads(raw)
        return Job(
            payload=uuid.UUID(data["payload"]),
            job_id=uuid.UUID(data["job_id"]),
            status=JobStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
        )
