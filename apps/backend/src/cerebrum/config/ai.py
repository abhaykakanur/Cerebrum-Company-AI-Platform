"""AI/RAG provider configuration — CIS Phase 4 Prompt 1's LLM
Abstraction. Every provider's API key is optional and ``None`` by
default: unlike the datastore credentials in ``config/database.py``,
``config/redis.py``, etc., no external LLM provider is required for the
platform to boot or for the RAG pipeline to run — ``local`` (see
cerebrum.infrastructure.llm.local_provider.LocalProvider) needs no
credential at all. Because these are optional and not "protects
something by default" secrets, they are deliberately absent from
``Settings._reject_default_secrets`` — an unconfigured
``OPENAI_API_KEY`` is a normal, supported state, not a security
vulnerability.
"""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from cerebrum.config import ENV_FILE


class AISettings(BaseSettings):
    """Provider selection, credentials, and default generation
    parameters for CIS Phase 4 Prompt 1's RAG engine.
    """

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_prefix="AI_",
        extra="ignore",
    )

    default_provider: str = Field(
        default="local",
        description="Provider used when a request does not specify one — one of "
        "'openai', 'anthropic', 'gemini', 'ollama', 'local'. AI_DEFAULT_PROVIDER.",
    )
    default_temperature: float = Field(
        default=0.2, ge=0.0, le=2.0, description="AI_DEFAULT_TEMPERATURE."
    )
    default_max_tokens: int = Field(
        default=1024, ge=1, le=32_000, description="AI_DEFAULT_MAX_TOKENS."
    )
    default_max_context_tokens: int = Field(
        default=3000,
        ge=1,
        description="Token budget for retrieved context — see "
        "cerebrum.application.ai.prompt_builder_service. "
        "AI_DEFAULT_MAX_CONTEXT_TOKENS.",
    )
    request_timeout_seconds: float = Field(
        default=60.0, gt=0.0, description="AI_REQUEST_TIMEOUT_SECONDS."
    )

    openai_api_key: SecretStr | None = Field(
        default=None, description="AI_OPENAI_API_KEY."
    )
    openai_base_url: str = Field(
        default="https://api.openai.com/v1", description="AI_OPENAI_BASE_URL."
    )
    openai_default_model: str = Field(
        default="gpt-4o-mini", description="AI_OPENAI_DEFAULT_MODEL."
    )

    anthropic_api_key: SecretStr | None = Field(
        default=None, description="AI_ANTHROPIC_API_KEY."
    )
    anthropic_base_url: str = Field(
        default="https://api.anthropic.com", description="AI_ANTHROPIC_BASE_URL."
    )
    anthropic_default_model: str = Field(
        default="claude-3-5-haiku-20241022", description="AI_ANTHROPIC_DEFAULT_MODEL."
    )

    gemini_api_key: SecretStr | None = Field(
        default=None, description="AI_GEMINI_API_KEY."
    )
    gemini_base_url: str = Field(
        default="https://generativelanguage.googleapis.com",
        description="AI_GEMINI_BASE_URL.",
    )
    gemini_default_model: str = Field(
        default="gemini-1.5-flash", description="AI_GEMINI_DEFAULT_MODEL."
    )

    ollama_base_url: str = Field(
        default="http://localhost:11434", description="AI_OLLAMA_BASE_URL."
    )
    ollama_default_model: str = Field(
        default="llama3.1", description="AI_OLLAMA_DEFAULT_MODEL."
    )

    local_default_model: str = Field(
        default="local-extractive-v1",
        description="Identifies "
        "cerebrum.infrastructure.llm.local_provider.LocalProvider's deterministic, "
        "dependency-free extractive summarizer — never a real generative model. "
        "AI_LOCAL_DEFAULT_MODEL.",
    )
