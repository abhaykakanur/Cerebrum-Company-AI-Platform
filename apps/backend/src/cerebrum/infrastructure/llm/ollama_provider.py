"""``OllamaProvider``: an ``LLMProvider`` adapter over a local Ollama
server's Chat API (``POST {base_url}/api/chat``) — see
https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-chat-completion.
Ollama streams newline-delimited JSON objects, not Server-Sent Events
(no ``data:`` prefix, no ``[DONE]`` sentinel — the last object carries
``"done": true`` instead) — the one adapter in this package that does
not use cerebrum.infrastructure.llm._sse.
"""

import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from cerebrum.infrastructure.llm.provider import (
    LLMMessage,
    LLMProviderError,
    LLMResponse,
    LLMUsage,
)


class OllamaProvider:
    name = "ollama"

    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient,
        base_url: str,
        default_model: str,
    ) -> None:
        self._client = http_client
        self._base_url = base_url.rstrip("/")
        self.default_model = default_model

    def _payload(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None,
        temperature: float,
        max_tokens: int,
        stream: bool,
    ) -> dict[str, Any]:
        return {
            "model": model or self.default_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": stream,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }

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
                f"{self._base_url}/api/chat", json=payload
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Ollama request failed: {exc}") from exc

        body = response.json()
        try:
            content = body["message"]["content"]
        except KeyError as exc:
            raise LLMProviderError(
                f"Ollama response missing expected fields: {exc}"
            ) from exc

        return LLMResponse(
            content=content,
            model=body.get("model", payload["model"]),
            provider=self.name,
            usage=LLMUsage(
                prompt_tokens=body.get("prompt_eval_count", 0),
                completion_tokens=body.get("eval_count", 0),
            ),
            finish_reason=body.get("done_reason"),
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
                "POST", f"{self._base_url}/api/chat", json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = event.get("message", {}).get("content")
                    if token:
                        yield token
                    if event.get("done"):
                        break
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Ollama stream failed: {exc}") from exc
