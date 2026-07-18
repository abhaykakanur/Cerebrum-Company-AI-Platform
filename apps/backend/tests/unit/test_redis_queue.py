"""Proves ``RedisQueue`` (CIS Phase 2 Prompt 2's Background Processing
framework) against a minimal in-memory fake standing in for
``redis.asyncio.Redis`` — the same pattern test_rate_limiter.py
established, extended here to the three list operations
(``rpush``/``lpop``/``llen``) this queue uses.
"""

import uuid

import pytest

from cerebrum.infrastructure.queue.redis_queue import RedisQueue
from cerebrum.workers.base import Job

pytestmark = pytest.mark.unit


class _FakeRedis:
    def __init__(self) -> None:
        self._lists: dict[str, list[str]] = {}

    async def rpush(self, key: str, value: str) -> int:
        self._lists.setdefault(key, []).append(value)
        return len(self._lists[key])

    async def lpop(self, key: str) -> str | None:
        values = self._lists.get(key, [])
        return values.pop(0) if values else None

    async def llen(self, key: str) -> int:
        return len(self._lists.get(key, []))


async def test_enqueue_then_dequeue_round_trips_the_payload() -> None:
    queue = RedisQueue(_FakeRedis())  # type: ignore[arg-type]
    payload_id = uuid.uuid4()

    await queue.enqueue(Job(payload=payload_id))
    dequeued = await queue.dequeue()

    assert dequeued is not None
    assert dequeued.payload == payload_id


async def test_dequeue_from_an_empty_queue_returns_none() -> None:
    queue = RedisQueue(_FakeRedis())  # type: ignore[arg-type]

    assert await queue.dequeue() is None


async def test_queue_is_fifo() -> None:
    queue = RedisQueue(_FakeRedis())  # type: ignore[arg-type]
    first, second = uuid.uuid4(), uuid.uuid4()

    await queue.enqueue(Job(payload=first))
    await queue.enqueue(Job(payload=second))

    assert (await queue.dequeue()).payload == first  # type: ignore[union-attr]
    assert (await queue.dequeue()).payload == second  # type: ignore[union-attr]


async def test_size_reflects_pending_items() -> None:
    queue = RedisQueue(_FakeRedis())  # type: ignore[arg-type]
    assert await queue.size() == 0

    await queue.enqueue(Job(payload=uuid.uuid4()))
    await queue.enqueue(Job(payload=uuid.uuid4()))
    assert await queue.size() == 2

    await queue.dequeue()
    assert await queue.size() == 1


async def test_different_queue_keys_are_independent() -> None:
    redis = _FakeRedis()
    queue_a = RedisQueue(redis, queue_key="queue-a")  # type: ignore[arg-type]
    queue_b = RedisQueue(redis, queue_key="queue-b")  # type: ignore[arg-type]

    await queue_a.enqueue(Job(payload=uuid.uuid4()))

    assert await queue_a.size() == 1
    assert await queue_b.size() == 0
