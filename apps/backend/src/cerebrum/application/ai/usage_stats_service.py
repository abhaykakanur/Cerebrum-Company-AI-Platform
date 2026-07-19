"""``AIUsageStatsService``: backs CIS Phase 4 Prompt 1's Conversation
Statistics API with real, cross-process aggregate counters — question
count and prompt/completion token totals per workspace and per
provider — stored as a Redis hash (already-provisioned infrastructure;
no new PostgreSQL table/migration for this milestone's scope). This is
deliberately not "conversation memory" (the excluded feature): no
question text, answer text, or per-conversation transcript is ever
stored here, only aggregate numbers that reset if the key is evicted.
"""

import uuid
from typing import Any

from redis.asyncio import Redis

_KEY_PREFIX = "ai:usage:"


def _key(workspace_id: uuid.UUID) -> str:
    return f"{_KEY_PREFIX}{workspace_id}"


class AIUsageStatsService:
    def __init__(self, *, redis: Redis) -> None:
        self._redis = redis

    async def record(
        self,
        *,
        workspace_id: uuid.UUID,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        key = _key(workspace_id)
        await self._redis.hincrby(key, "question_count", 1)
        await self._redis.hincrby(key, "prompt_tokens", prompt_tokens)
        await self._redis.hincrby(key, "completion_tokens", completion_tokens)
        await self._redis.hincrby(key, f"provider:{provider}", 1)

    async def get_statistics(self, *, workspace_id: uuid.UUID) -> dict[str, Any]:
        raw = await self._redis.hgetall(_key(workspace_id))
        decoded = {
            (k.decode() if isinstance(k, bytes) else k): (
                v.decode() if isinstance(v, bytes) else v
            )
            for k, v in raw.items()
        }
        providers = {
            field.removeprefix("provider:"): int(value)
            for field, value in decoded.items()
            if field.startswith("provider:")
        }
        return {
            "question_count": int(decoded.get("question_count", 0)),
            "prompt_tokens": int(decoded.get("prompt_tokens", 0)),
            "completion_tokens": int(decoded.get("completion_tokens", 0)),
            "providers": providers,
        }
