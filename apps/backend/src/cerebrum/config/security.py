"""Transport-security configuration: allowed hosts and CORS origins.

Scope note: this module deliberately does NOT hold credentials, signing
keys, or API keys — those are Secrets per
docs/architecture/specification/37_Configuration_Strategy.md, owned by the
Security Domain's future ``GetSecret`` port, not read here. This module
only holds the non-secret HTTP-transport policy needed to configure
TrustedHostMiddleware and CORSMiddleware (see cerebrum.middleware).
"""

from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class SecuritySettings(BaseSettings):
    """Allowed-host and CORS policy. No defaults here are safe for
    production as-is — see ``Settings``'s model validator in
    cerebrum.config.settings, which enforces that production overrides
    the permissive local development defaults below.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SECURITY_",
        extra="ignore",
    )

    # NoDecode: pydantic-settings otherwise tries to JSON-decode any
    # list-typed field's raw environment string (expecting `["a","b"]`)
    # before our own comma-separated parsing below ever runs. NoDecode
    # skips that JSON attempt so `_split_comma_separated` — a plain,
    # human-writable `.env` format — is what actually executes.
    trusted_hosts: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["*"],
        description="Host headers TrustedHostMiddleware accepts. "
        "SECURITY_TRUSTED_HOSTS (comma-separated). '*' is a "
        "development-only default.",
    )
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        description="Origins CORSMiddleware accepts. SECURITY_CORS_ALLOWED_ORIGINS "
        "(comma-separated).",
    )

    @field_validator("trusted_hosts", "cors_allowed_origins", mode="before")
    @classmethod
    def _split_comma_separated(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value
