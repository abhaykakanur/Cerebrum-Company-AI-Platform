"""Provider selection — CIS Phase 4 Prompt 1's "providers must be
pluggable" requirement. :func:`build_llm_provider` is the one place
that maps a provider *name* (a plain string — from configuration or a
per-request API parameter) to a concrete ``LLMProvider`` instance;
nothing above cerebrum.dependencies.ai imports a provider class
directly. :func:`available_providers` backs the ``/ai/config`` API —
which providers this deployment could select right now, given its
current environment configuration (never a live connectivity probe —
see ``OllamaProvider``'s docstring on why availability here means
"configured," not "reachable").
"""

import httpx
from pydantic import SecretStr

from cerebrum.config.ai import AISettings
from cerebrum.infrastructure.llm.anthropic_provider import AnthropicProvider
from cerebrum.infrastructure.llm.gemini_provider import GeminiProvider
from cerebrum.infrastructure.llm.local_provider import LocalProvider
from cerebrum.infrastructure.llm.ollama_provider import OllamaProvider
from cerebrum.infrastructure.llm.openai_provider import OpenAIProvider
from cerebrum.infrastructure.llm.provider import LLMProvider
from cerebrum.shared.errors.exceptions import ValidationException

_ALWAYS_AVAILABLE = ("local", "ollama")
_KEY_GATED = ("openai", "anthropic", "gemini")
SUPPORTED_PROVIDER_NAMES = (*_ALWAYS_AVAILABLE, *_KEY_GATED)


def available_providers(settings: AISettings) -> list[str]:
    available = list(_ALWAYS_AVAILABLE)
    if settings.openai_api_key is not None:
        available.append("openai")
    if settings.anthropic_api_key is not None:
        available.append("anthropic")
    if settings.gemini_api_key is not None:
        available.append("gemini")
    return available


def build_llm_provider(
    name: str, *, settings: AISettings, http_client: httpx.AsyncClient
) -> LLMProvider:
    if name == "local":
        return LocalProvider(default_model=settings.local_default_model)
    if name == "ollama":
        return OllamaProvider(
            http_client=http_client,
            base_url=settings.ollama_base_url,
            default_model=settings.ollama_default_model,
        )
    if name == "openai":
        return OpenAIProvider(
            http_client=http_client,
            api_key=_require_key(name, settings.openai_api_key),
            base_url=settings.openai_base_url,
            default_model=settings.openai_default_model,
        )
    if name == "anthropic":
        return AnthropicProvider(
            http_client=http_client,
            api_key=_require_key(name, settings.anthropic_api_key),
            base_url=settings.anthropic_base_url,
            default_model=settings.anthropic_default_model,
        )
    if name == "gemini":
        return GeminiProvider(
            http_client=http_client,
            api_key=_require_key(name, settings.gemini_api_key),
            base_url=settings.gemini_base_url,
            default_model=settings.gemini_default_model,
        )
    raise ValidationException(
        f"Unknown LLM provider '{name}'. Supported providers: "
        f"{', '.join(SUPPORTED_PROVIDER_NAMES)}."
    )


def _require_key(name: str, secret: SecretStr | None) -> str:
    if secret is None:
        raise ValidationException(
            f"Provider '{name}' is not configured on this deployment "
            f"(its API key is unset)."
        )
    return secret.get_secret_value()
