"""The composed, validated configuration root.

``Settings`` aggregates every subsystem's typed configuration module into
one immutable object, loaded exactly once per process via
:func:`get_settings`. Application code SHALL depend on this module (or the
``SettingsDep`` provider in cerebrum.dependencies.settings) — never on
``os.environ`` directly — per
docs/architecture/specification/37_Configuration_Strategy.md's Environment
Variables architecture.
"""

from functools import lru_cache

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from cerebrum.config.api import APISettings
from cerebrum.config.application import ApplicationSettings
from cerebrum.config.database import PostgresSettings
from cerebrum.config.infrastructure import InfrastructureSettings
from cerebrum.config.logging import LoggingSettings
from cerebrum.config.minio import MinIOSettings
from cerebrum.config.monitoring import MonitoringSettings
from cerebrum.config.neo4j import Neo4jSettings
from cerebrum.config.opensearch import OpenSearchSettings
from cerebrum.config.qdrant import QdrantSettings
from cerebrum.config.redis import RedisSettings
from cerebrum.config.security import SecuritySettings
from cerebrum.config.worker import WorkerSettings
from cerebrum.shared.errors.exceptions import ConfigurationException

# Every datastore credential and the JWT signing secret share this
# prefix in their local-development default (see config/database.py,
# config/redis.py, config/neo4j.py, config/minio.py, config/security.py)
# — a single, greppable marker of "never actually used to protect
# anything," per docs/architecture/specification/37_Configuration_Strategy.md's
# secret-handling guidance. CIS Phase 1 Prompt 7's Configuration Hardening/
# Security Review: a production-like environment booting with even one of
# these unrotated is a silent, critical vulnerability (e.g. an unrotated
# JWT_SIGNING_SECRET is a value published in this very repository,
# letting anyone forge a valid access token) — the pre-existing
# trusted_hosts/cors_allowed_origins checks below caught the transport-
# security case but not this one.
_DEFAULT_SECRET_PLACEHOLDER = "changeme-local-only"


class Settings(BaseSettings):
    """The single, typed configuration root. Immutable once constructed —
    a changed environment variable requires a process restart, per
    docs/architecture/specification/37_Configuration_Strategy.md (runtime,
    hot-reloadable configuration is the Configuration Domain's concern,
    a future business feature, not this platform-level object's).
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", frozen=True
    )

    application: ApplicationSettings = Field(default_factory=ApplicationSettings)
    api: APISettings = Field(default_factory=APISettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    infrastructure: InfrastructureSettings = Field(
        default_factory=InfrastructureSettings
    )
    neo4j: Neo4jSettings = Field(default_factory=Neo4jSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    minio: MinIOSettings = Field(default_factory=MinIOSettings)
    opensearch: OpenSearchSettings = Field(default_factory=OpenSearchSettings)
    worker: WorkerSettings = Field(default_factory=WorkerSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)

    @model_validator(mode="after")
    def _validate_for_environment(self) -> "Settings":
        """No invalid configuration may allow the application to start —
        see docs/architecture/specification/37_Configuration_Strategy.md's
        Configuration Validation requirement. Production-like environments
        cannot use the permissive local-development transport-security
        defaults.
        """
        if self.application.environment.is_production_like:
            if "*" in self.security.trusted_hosts:
                raise ConfigurationException(
                    message="SECURITY_TRUSTED_HOSTS cannot be '*' in a "
                    f"'{self.application.environment.value}' environment.",
                    context={"environment": self.application.environment.value},
                )
            if any(origin == "*" for origin in self.security.cors_allowed_origins):
                raise ConfigurationException(
                    message="SECURITY_CORS_ALLOWED_ORIGINS cannot contain '*' in a "
                    f"'{self.application.environment.value}' environment.",
                    context={"environment": self.application.environment.value},
                )
            self._reject_default_secrets()
        return self

    def _reject_default_secrets(self) -> None:
        """No local-development placeholder credential may reach a
        production-like environment unrotated — see this module's
        ``_DEFAULT_SECRET_PLACEHOLDER`` docstring.
        """
        secrets: tuple[tuple[str, str | SecretStr], ...] = (
            ("POSTGRES_PASSWORD", self.postgres.password),
            ("REDIS_PASSWORD", self.redis.password),
            ("NEO4J_PASSWORD", self.neo4j.password),
            ("MINIO_ACCESS_KEY", self.minio.access_key),
            ("MINIO_SECRET_KEY", self.minio.secret_key),
            ("JWT_SIGNING_SECRET", self.security.jwt_secret_key),
        )
        for env_var, value in secrets:
            raw = value.get_secret_value() if isinstance(value, SecretStr) else value
            if raw.startswith(_DEFAULT_SECRET_PLACEHOLDER):
                raise ConfigurationException(
                    message=f"{env_var} is still set to its local-development "
                    f"placeholder value in a "
                    f"'{self.application.environment.value}' environment. It "
                    "must be rotated to a real secret before this process may "
                    "start.",
                    context={
                        "environment": self.application.environment.value,
                        "variable": env_var,
                    },
                )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """The process-wide Settings singleton. Cached so every caller — the
    Application Factory, every DI provider, every middleware — observes
    the same instance without re-parsing the environment. Tests that need
    a fresh instance under different environment variables should call
    :func:`get_settings.cache_clear` first (see apps/backend/tests/conftest.py).
    """
    return Settings()
