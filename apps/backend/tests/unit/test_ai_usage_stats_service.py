"""Proves CIS Phase 4 Prompt 1's ``AIUsageStatsService``: Redis-backed
aggregate counters, scoped per workspace, incremented correctly across
repeated calls and multiple providers — against a minimal in-memory
fake standing in for ``redis.asyncio.Redis`` (only ``hincrby``/
``hgetall``, the two calls this service makes), mirroring
apps/backend/tests/unit/test_rate_limiter.py's ``_FakeRedis`` pattern.
"""

import uuid

import pytest

from cerebrum.application.ai.usage_stats_service import AIUsageStatsService

pytestmark = pytest.mark.unit


class _FakeRedis:
    def __init__(self) -> None:
        self._hashes: dict[str, dict[bytes, bytes]] = {}

    async def hincrby(self, key: str, field: str, amount: int = 1) -> int:
        hash_ = self._hashes.setdefault(key, {})
        current = int(hash_.get(field.encode(), b"0"))
        updated = current + amount
        hash_[field.encode()] = str(updated).encode()
        return updated

    async def hgetall(self, key: str) -> dict[bytes, bytes]:
        return self._hashes.get(key, {})


async def test_record_increments_question_count_and_tokens() -> None:
    service = AIUsageStatsService(redis=_FakeRedis())  # type: ignore[arg-type]
    workspace_id = uuid.uuid4()

    await service.record(
        workspace_id=workspace_id,
        provider="local",
        prompt_tokens=100,
        completion_tokens=20,
    )
    await service.record(
        workspace_id=workspace_id,
        provider="local",
        prompt_tokens=50,
        completion_tokens=10,
    )

    stats = await service.get_statistics(workspace_id=workspace_id)

    assert stats["question_count"] == 2
    assert stats["prompt_tokens"] == 150
    assert stats["completion_tokens"] == 30


async def test_record_tracks_per_provider_counts() -> None:
    service = AIUsageStatsService(redis=_FakeRedis())  # type: ignore[arg-type]
    workspace_id = uuid.uuid4()

    await service.record(
        workspace_id=workspace_id,
        provider="openai",
        prompt_tokens=1,
        completion_tokens=1,
    )
    await service.record(
        workspace_id=workspace_id,
        provider="local",
        prompt_tokens=1,
        completion_tokens=1,
    )
    await service.record(
        workspace_id=workspace_id,
        provider="openai",
        prompt_tokens=1,
        completion_tokens=1,
    )

    stats = await service.get_statistics(workspace_id=workspace_id)

    assert stats["providers"] == {"openai": 2, "local": 1}


async def test_get_statistics_returns_zero_for_unknown_workspace() -> None:
    service = AIUsageStatsService(redis=_FakeRedis())  # type: ignore[arg-type]

    stats = await service.get_statistics(workspace_id=uuid.uuid4())

    assert stats == {
        "question_count": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "providers": {},
    }


async def test_statistics_are_scoped_per_workspace() -> None:
    redis = _FakeRedis()
    service = AIUsageStatsService(redis=redis)  # type: ignore[arg-type]
    workspace_a, workspace_b = uuid.uuid4(), uuid.uuid4()

    await service.record(
        workspace_id=workspace_a,
        provider="local",
        prompt_tokens=10,
        completion_tokens=1,
    )

    stats_a = await service.get_statistics(workspace_id=workspace_a)
    stats_b = await service.get_statistics(workspace_id=workspace_b)

    assert stats_a["question_count"] == 1
    assert stats_b["question_count"] == 0
