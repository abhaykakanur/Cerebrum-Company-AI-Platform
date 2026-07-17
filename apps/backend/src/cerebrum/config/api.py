"""HTTP server binding and API surface configuration.

See docs/architecture/specification/80_API_Architecture.md and
docs/architecture/specification/81_API_Standards.md (API Versioning).
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseSettings):
    """Where the ASGI server binds, and the API's versioning surface."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="BACKEND_",
        extra="ignore",
    )

    host: str = Field(default="0.0.0.0", description="Bind address. BACKEND_HOST.")
    port: int = Field(
        default=8000, ge=1, le=65535, description="Bind port. BACKEND_PORT."
    )

    api_v1_prefix: str = Field(
        default="/api/v1",
        description="URL prefix for the versioned API surface — Major Versions per "
        "docs/architecture/specification/81_API_Standards.md's API Versioning section.",
    )

    @field_validator("api_v1_prefix")
    @classmethod
    def _prefix_must_start_with_slash(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("api_v1_prefix must start with '/'")
        return value.rstrip("/")
