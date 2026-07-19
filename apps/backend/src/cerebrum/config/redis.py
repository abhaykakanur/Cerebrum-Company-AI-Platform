"""Redis connection configuration.

Owns the ``REDIS_*`` environment variables defined in `.env.example`.
Redis serves as cache, session store, rate-limit counter store, and
Celery broker — see docs/architecture/specification/32_Technology_Stack.md.
"""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from cerebrum.config import ENV_FILE


class RedisSettings(BaseSettings):
    """Connection parameters for the cache/session/broker datastore."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_prefix="REDIS_",
        extra="ignore",
    )

    host: str = Field(default="localhost", description="REDIS_HOST.")
    port: int = Field(default=6379, ge=1, le=65535, description="REDIS_PORT.")
    password: SecretStr = Field(
        default=SecretStr("changeme-local-only"), description="REDIS_PASSWORD."
    )

    @property
    def dsn(self) -> str:
        """A ``redis://`` connection URI, used by
        :class:`~cerebrum.infrastructure.cache.manager.RedisClientManager`.
        """
        return f"redis://:{self.password.get_secret_value()}@{self.host}:{self.port}/0"
