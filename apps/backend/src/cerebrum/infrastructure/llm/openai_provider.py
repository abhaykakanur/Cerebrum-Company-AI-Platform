"""``OpenAIProvider``: an ``LLMProvider`` adapter over OpenAI's Chat
Completions API (``POST {base_url}/chat/completions``) — see
https://platform.openai.com/docs/api-reference/chat. Also the adapter
any OpenAI-API-compatible self-hosted server (vLLM, LM Studio, etc.)
can reuse by pointing ``base_url`` at it, so it doubles as this
package's "OpenAI-compatible" adapter without a separate class.
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


class OpenAIProvider:
    name = "openai"

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
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

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
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
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
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"OpenAI request failed: {exc}") from exc

        body = response.json()
        try:
            choice = body["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LLMProviderError(
                f"OpenAI response missing expected fields: {exc}"
            ) from exc

        usage = body.get("usage", {})
        return LLMResponse(
            content=content,
            model=body.get("model", payload["model"]),
            provider=self.name,
            usage=LLMUsage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
            ),
            finish_reason=choice.get("finish_reason"),
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
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=self._headers(),
            ) as response:
                response.raise_for_status()
                async for data in iter_sse_data(response):
                    if data == "[DONE]":
                        break
                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = event.get("choices") or [{}]
                    token = choices[0].get("delta", {}).get("content")
                    if token:
                        yield token
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"OpenAI stream failed: {exc}") from exc
