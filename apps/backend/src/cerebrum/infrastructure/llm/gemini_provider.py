"""``GeminiProvider``: an ``LLMProvider`` adapter over Google's
Generative Language API
(``POST {base_url}/v1beta/models/{model}:generateContent``) — see
https://ai.google.dev/api/generate-content. Gemini's wire format
diverges from OpenAI/Anthropic/Ollama in three ways this adapter
absorbs: the API key is a query parameter (not a header), the system
prompt is a ``systemInstruction`` field, and the assistant's own role
is named ``"model"`` rather than ``"assistant"``.
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


class GeminiProvider:
    name = "gemini"

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

    @staticmethod
    def _split_system(
        messages: list[LLMMessage],
    ) -> tuple[str, list[dict[str, Any]]]:
        system_parts = [m.content for m in messages if m.role == "system"]
        contents = [
            {
                "role": "model" if m.role == "assistant" else "user",
                "parts": [{"text": m.content}],
            }
            for m in messages
            if m.role != "system"
        ]
        return "\n\n".join(system_parts), contents

    def _payload(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        system, contents = self._split_system(messages)
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        return payload

    def _url(self, *, model: str, method: str, stream: bool) -> str:
        suffix = "?alt=sse&key=" if stream else "?key="
        return f"{self._base_url}/v1beta/models/{model}:{method}{suffix}{self._api_key}"

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        request_id: uuid.UUID | None = None,
    ) -> LLMResponse:
        resolved_model = model or self.default_model
        payload = self._payload(
            messages, temperature=temperature, max_tokens=max_tokens
        )
        try:
            response = await self._client.post(
                self._url(model=resolved_model, method="generateContent", stream=False),
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Gemini request failed: {exc}") from exc

        body = response.json()
        try:
            candidate = body["candidates"][0]
            content = "".join(
                part.get("text", "") for part in candidate["content"]["parts"]
            )
        except (KeyError, IndexError) as exc:
            raise LLMProviderError(
                f"Gemini response missing expected fields: {exc}"
            ) from exc

        usage = body.get("usageMetadata", {})
        return LLMResponse(
            content=content,
            model=resolved_model,
            provider=self.name,
            usage=LLMUsage(
                prompt_tokens=usage.get("promptTokenCount", 0),
                completion_tokens=usage.get("candidatesTokenCount", 0),
            ),
            finish_reason=candidate.get("finishReason"),
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
        resolved_model = model or self.default_model
        payload = self._payload(
            messages, temperature=temperature, max_tokens=max_tokens
        )
        try:
            async with self._client.stream(
                "POST",
                self._url(
                    model=resolved_model, method="streamGenerateContent", stream=True
                ),
                json=payload,
            ) as response:
                response.raise_for_status()
                async for data in iter_sse_data(response):
                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    candidates = event.get("candidates") or [{}]
                    parts = candidates[0].get("content", {}).get("parts", [])
                    token = "".join(part.get("text", "") for part in parts)
                    if token:
                        yield token
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Gemini stream failed: {exc}") from exc
