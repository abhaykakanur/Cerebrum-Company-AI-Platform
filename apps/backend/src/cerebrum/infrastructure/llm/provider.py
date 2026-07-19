"""The provider-independent LLM interface — CIS Phase 4 Prompt 1's
``LLMProvider`` service. Every concrete adapter in this package
(OpenAI/Anthropic/Gemini/Ollama/Local) implements this ``Protocol``;
cerebrum.application.ai never imports a provider-specific SDK or
request/response shape, only these three types — see
docs/architecture/specification/60_AI_Model_Abstraction.md's Provider
Independence Principle ("no AI Subsystem Layer... SHALL contain a
conditional branch keyed on which provider is active").
"""

import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Literal, Protocol

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True, slots=True)
class LLMMessage:
    role: Role
    content: str


@dataclass(frozen=True, slots=True)
class LLMUsage:
    prompt_tokens: int
    completion_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass(frozen=True, slots=True)
class LLMResponse:
    content: str
    model: str
    provider: str
    usage: LLMUsage
    finish_reason: str | None = None


class LLMProviderError(Exception):
    """Raised when a provider adapter cannot complete a request (a
    non-2xx HTTP response, malformed response body, or network
    failure) — deliberately provider-shape-free (a message string, not
    a provider-specific exception type), so callers never need to
    import a provider SDK's exception hierarchy to handle failure.
    """


class LLMProvider(Protocol):
    """CIS Phase 4 Prompt 1's ``LLMProvider`` port. ``name`` identifies
    the adapter (``"openai"``, ``"anthropic"``, ``"gemini"``,
    ``"ollama"``, ``"local"``) for logging/events/citations —
    cerebrum.application.ai never branches on it, only records it.
    """

    name: str
    default_model: str

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        request_id: uuid.UUID | None = None,
    ) -> LLMResponse: ...

    def stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        request_id: uuid.UUID | None = None,
    ) -> AsyncGenerator[str, None]: ...
