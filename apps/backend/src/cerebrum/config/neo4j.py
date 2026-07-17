"""Neo4j connection configuration.

Owns the ``NEO4J_*`` environment variables defined in `.env.example`. See
docs/architecture/specification/42_Database_Responsibilities.md for
Neo4j's role as the authoritative relationship datastore.
"""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Neo4jSettings(BaseSettings):
    """Connection parameters for the graph datastore."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="NEO4J_",
        extra="ignore",
    )

    host: str = Field(default="localhost", description="NEO4J_HOST.")
    http_port: int = Field(default=7474, ge=1, le=65535, description="NEO4J_HTTP_PORT.")
    port: int = Field(
        default=7687, ge=1, le=65535, description="Bolt port. NEO4J_PORT."
    )
    user: str = Field(default="neo4j", description="NEO4J_USER.")
    password: SecretStr = Field(
        default=SecretStr("changeme-local-only"), description="NEO4J_PASSWORD."
    )

    @property
    def bolt_uri(self) -> str:
        """A ``bolt://`` connection URI, used by
        :class:`~cerebrum.infrastructure.graph.manager.Neo4jClientManager`.
        """
        return f"bolt://{self.host}:{self.port}"
