"""Security configuration: transport-security policy (allowed hosts,
CORS), and — as of CIS Phase 1 Prompt 5 — the Identity & Security
platform's own settings (JWT, password policy, rate limiting, session
timeout, API key expiration).

Scope note on ``jwt_secret_key``: per
docs/architecture/specification/37_Configuration_Strategy.md, secrets
belong behind the Security Domain's future ``GetSecret`` port, not a
typed ``Settings`` field, in production. That port does not exist yet.
This module follows the same interim pattern already established for
datastore credentials in this codebase
(:class:`~cerebrum.config.database.PostgresSettings.password`,
:class:`~cerebrum.config.redis.RedisSettings.dsn`'s embedded password,
etc.): a ``SecretStr`` field read from an environment variable
(``JWT_SIGNING_SECRET`` — already documented in `.env.example` since
Phase 1 Prompt 1, before any code read it), acceptable for local
development and until the Security Domain's real secrets backend is
built, never logged (see cerebrum.core.logging's redaction denylist,
which already includes ``jwt``/``secret``/``token``).
"""

from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class SecuritySettings(BaseSettings):
    """Allowed-host/CORS policy plus the Identity & Security platform's
    configuration. No defaults here are safe for production as-is — see
    ``Settings``'s model validator in cerebrum.config.settings, which
    enforces that production overrides the permissive local development
    transport-security defaults below.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SECURITY_",
        extra="ignore",
        # Without this, `jwt_secret_key`'s `validation_alias` below means
        # *only* the alias ("JWT_SIGNING_SECRET") would be accepted as a
        # constructor keyword — `SecuritySettings(jwt_secret_key=...)`
        # would silently fall back to the field's default instead of
        # raising, since `extra="ignore"` swallows the unrecognized
        # keyword. populate_by_name=True accepts both the alias and the
        # Python field name, matching every other field in this class.
        populate_by_name=True,
    )

    # --- Transport security (Phase 1, Prompt 3) ------------------------------
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
    trusted_proxies: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["127.0.0.1", "::1"],
        description="IP addresses whose X-Forwarded-For header is trusted when "
        "resolving a request's real client IP — see "
        "cerebrum.middleware.request_context. SECURITY_TRUSTED_PROXIES "
        "(comma-separated). Untrusted by default beyond loopback: a "
        "reverse proxy's actual address must be listed explicitly.",
    )
    max_request_body_bytes: int = Field(
        default=10 * 1024 * 1024,
        gt=0,
        description="Hard ceiling enforced by RequestSizeLimitMiddleware — see "
        "cerebrum.middleware.request_size_limit. SECURITY_MAX_REQUEST_BODY_BYTES.",
    )

    @field_validator(
        "trusted_hosts", "cors_allowed_origins", "trusted_proxies", mode="before"
    )
    @classmethod
    def _split_comma_separated(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    # --- JWT (Phase 1, Prompt 5) ----------------------------------------------
    jwt_secret_key: SecretStr = Field(
        default=SecretStr("changeme-local-only-do-not-use-in-production"),
        description="HMAC signing key for access/refresh tokens — see this "
        "module's docstring. JWT_SIGNING_SECRET (no SECURITY_ prefix: this "
        "variable predates this settings class — see `.env.example`).",
        validation_alias="JWT_SIGNING_SECRET",
    )
    jwt_algorithm: str = Field(
        default="HS256", description="PyJWT algorithm name. SECURITY_JWT_ALGORITHM."
    )

    @field_validator("jwt_algorithm")
    @classmethod
    def _jwt_algorithm_must_be_a_known_safe_signing_algorithm(cls, value: str) -> str:
        """Rejects ``"none"`` and anything else PyJWT doesn't implement —
        CIS Phase 1 Prompt 7's Security Review ("JWT configuration").
        ``jwt_algorithm`` is environment-configurable
        (``SECURITY_JWT_ALGORITHM``); without this check, a misconfigured
        or malicious value of ``"none"`` reaching
        :meth:`~cerebrum.infrastructure.security.jwt.TokenService.decode_token`'s
        ``algorithms=[...]`` allowlist would accept an unsigned token —
        the classic JWT "alg: none" vulnerability. This validates the
        *configured* algorithm name only; it does not by itself change
        ``TokenService``'s existing (already-correct) practice of always
        passing an explicit ``algorithms=`` allowlist to ``jwt.decode``.
        """
        allowed = {
            "HS256",
            "HS384",
            "HS512",
            "RS256",
            "RS384",
            "RS512",
            "ES256",
            "ES384",
            "ES512",
        }
        if value not in allowed:
            raise ValueError(
                f"jwt_algorithm must be one of {sorted(allowed)}, got {value!r}."
            )
        return value

    access_token_expire_minutes: int = Field(
        default=15,
        gt=0,
        description="Access token lifetime. Short-lived by design — the refresh "
        "token, not a long-lived access token, is what survives between "
        "sessions. SECURITY_ACCESS_TOKEN_EXPIRE_MINUTES.",
    )
    refresh_token_expire_days: int = Field(
        default=30,
        gt=0,
        description="Refresh token lifetime — also the ceiling for how long a "
        "revoked-but-not-yet-expired UserSession row remains meaningful. "
        "SECURITY_REFRESH_TOKEN_EXPIRE_DAYS.",
    )
    use_secure_cookies: bool = Field(
        default=False,
        description="Whether the login/refresh endpoints also set the refresh "
        "token as an HttpOnly cookie (future-ready — see "
        "docs/architecture/security/authentication-guide.md; no frontend "
        "consumes it yet). Independent of the JSON response body, which "
        "always includes both tokens. SECURITY_USE_SECURE_COOKIES.",
    )

    # --- Password policy (Phase 1, Prompt 5) ----------------------------------
    password_min_length: int = Field(
        default=12, ge=8, description="SECURITY_PASSWORD_MIN_LENGTH."
    )
    password_require_uppercase: bool = Field(
        default=True, description="SECURITY_PASSWORD_REQUIRE_UPPERCASE."
    )
    password_require_lowercase: bool = Field(
        default=True, description="SECURITY_PASSWORD_REQUIRE_LOWERCASE."
    )
    password_require_digit: bool = Field(
        default=True, description="SECURITY_PASSWORD_REQUIRE_DIGIT."
    )
    password_require_special: bool = Field(
        default=True, description="SECURITY_PASSWORD_REQUIRE_SPECIAL."
    )

    # --- Password hashing (Phase 1, Prompt 5) ---------------------------------
    # Argon2id parameters — see cerebrum.infrastructure.security.password.
    # Defaults are argon2-cffi's own recommended baseline; tuning these is an
    # operational (not architectural) decision, hence configurable rather
    # than hard-coded.
    password_hash_time_cost: int = Field(
        default=3, gt=0, description="SECURITY_PASSWORD_HASH_TIME_COST."
    )
    password_hash_memory_cost_kib: int = Field(
        default=65536, gt=0, description="SECURITY_PASSWORD_HASH_MEMORY_COST_KIB."
    )
    password_hash_parallelism: int = Field(
        default=4, gt=0, description="SECURITY_PASSWORD_HASH_PARALLELISM."
    )

    # --- Rate limiting (Phase 1, Prompt 5) ------------------------------------
    login_rate_limit_attempts: int = Field(
        default=5,
        gt=0,
        description="Max login attempts per window before throttling — see "
        "cerebrum.infrastructure.security.rate_limiter. "
        "SECURITY_LOGIN_RATE_LIMIT_ATTEMPTS.",
    )
    login_rate_limit_window_seconds: int = Field(
        default=300, gt=0, description="SECURITY_LOGIN_RATE_LIMIT_WINDOW_SECONDS."
    )

    # --- General API rate limiting (Phase 1, Prompt 6) ------------------------
    # Distinct from the login-specific limiter above: this is the default
    # ceiling for cerebrum.dependencies.rate_limit's Per User/Tenant/API
    # Key/Anonymous dependencies, which a future route opts into
    # individually — see docs/architecture/specification/81_API_Standards.md's
    # Rate Limiting section's five dimensions.
    api_rate_limit_requests: int = Field(
        default=120,
        gt=0,
        description="Default requests-per-window ceiling for the general-purpose "
        "rate limit dependencies. SECURITY_API_RATE_LIMIT_REQUESTS.",
    )
    api_rate_limit_window_seconds: int = Field(
        default=60, gt=0, description="SECURITY_API_RATE_LIMIT_WINDOW_SECONDS."
    )

    # --- Sessions & API keys (Phase 1, Prompt 5) ------------------------------
    session_idle_timeout_minutes: int = Field(
        default=43200,  # 30 days, matching the default refresh token lifetime.
        gt=0,
        description="A UserSession with no activity for this long is treated as "
        "expired even if its refresh token has not yet reached its own "
        "expiry. SECURITY_SESSION_IDLE_TIMEOUT_MINUTES.",
    )
    api_key_default_expire_days: int = Field(
        default=365,
        gt=0,
        description="Default expiration applied to a newly generated API key "
        "when the caller does not specify one. SECURITY_API_KEY_DEFAULT_EXPIRE_DAYS.",
    )
