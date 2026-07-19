"""PostgreSQL connection configuration.

Owns the ``POSTGRES_*`` environment variables defined in
`.env.example`. Consumed by
:class:`~cerebrum.infrastructure.database.manager.PostgresClientManager`
to build the async engine — this module itself only defines and
validates the *shape* of the connection configuration, per
docs/architecture/specification/42_Database_Responsibilities.md.
"""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from cerebrum.config import ENV_FILE


class PostgresSettings(BaseSettings):
    """Connection parameters for the authoritative relational datastore."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_prefix="POSTGRES_",
        extra="ignore",
    )

    host: str = Field(default="localhost", description="POSTGRES_HOST.")
    port: int = Field(default=5432, ge=1, le=65535, description="POSTGRES_PORT.")
    db: str = Field(default="cerebrum", description="POSTGRES_DB.")
    user: str = Field(default="cerebrum", description="POSTGRES_USER.")
    password: SecretStr = Field(
        default=SecretStr("changeme-local-only"), description="POSTGRES_PASSWORD."
    )

    @property
    def dsn(self) -> str:
        """A ``postgresql+asyncpg://`` DSN — the one place connection-string
        assembly happens, so no other module re-derives it ad hoc.
        """
        return (
            f"postgresql+asyncpg://{self.user}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.db}"
        )
