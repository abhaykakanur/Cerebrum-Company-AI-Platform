"""``AnthropicProvider``: an ``LLMProvider`` adapter over Anthropic's
Messages API (``POST {base_url}/v1/messages``) — see
https://docs.anthropic.com/en/api/messages. Anthropic's wire format
puts the system prompt in a top-level ``system`` field rather than a
``role: "system"`` message, unlike OpenAI/Gemini/Ollama — this adapter
is where that difference is absorbed, never leaking into
cerebrum.application.ai (see
docs/architecture/specification/60_AI_Model_Abstraction.md's Provider
Independence Principle).
"""

import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from cerebrum.infrastructure.llm._sse import iter_sse_data
from cerebrum.infrastructure.llm.provider import (
    LLMMessage,
    LLMProviderError,
    LLMResponse,
    LLMUsage,
)

_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider:
    name = "anthropic"

    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient,
        api_key: str,
        base_url: str,
        default_model: str,
    ) -> None:
        self._client = http_client
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self.default_model = default_model

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self._api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

    @staticmethod
    def _split_system(messages: list[LLMMessage]) -> tuple[str, list[dict[str, str]]]:
        system_parts = [m.content for m in messages if m.role == "system"]
        turns = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role != "system"
        ]
        return "\n\n".join(system_parts), turns

    def _payload(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None,
        temperature: float,
        max_tokens: int,
        stream: bool,
    ) -> dict[str, Any]:
        system, turns = self._split_system(messages)
        payload: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": turns,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }
        if system:
            payload["system"] = system
        return payload

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        request_id: uuid.UUID | None = None,
    ) -> LLMResponse:
        payload = self._payload(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        try:
            response = await self._client.post(
                f"{self._base_url}/v1/messages", json=payload, headers=self._headers()
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Anthropic request failed: {exc}") from exc

        body = response.json()
        try:
            content = "".join(
                block.get("text", "")
                for block in body["content"]
                if block.get("type") == "text"
            )
        except KeyError as exc:
            raise LLMProviderError(
                f"Anthropic response missing expected fields: {exc}"
            ) from exc

        usage = body.get("usage", {})
        return LLMResponse(
            content=content,
            model=body.get("model", payload["model"]),
            provider=self.name,
            usage=LLMUsage(
                prompt_tokens=usage.get("input_tokens", 0),
                completion_tokens=usage.get("output_tokens", 0),
            ),
            finish_reason=body.get("stop_reason"),
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        request_id: uuid.UUID | None = None,
    ) -> AsyncGenerator[str, None]:
        payload = self._payload(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        try:
            async with self._client.stream(
                "POST",
                f"{self._base_url}/v1/messages",
                json=payload,
                headers=self._headers(),
            ) as response:
                response.raise_for_status()
                async for data in iter_sse_data(response):
                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    if event.get("type") != "content_block_delta":
                        continue
                    token = event.get("delta", {}).get("text")
                    if token:
                        yield token
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Anthropic stream failed: {exc}") from exc
