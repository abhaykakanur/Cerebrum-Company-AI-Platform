"""Qdrant connection configuration.

Owns the ``QDRANT_*`` environment variables defined in `.env.example`.
See docs/architecture/specification/42_Database_Responsibilities.md for
Qdrant's role as the authoritative vector datastore.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from cerebrum.config import ENV_FILE


class QdrantSettings(BaseSettings):
    """Connection parameters for the vector datastore."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_prefix="QDRANT_",
        extra="ignore",
    )

    host: str = Field(default="localhost", description="QDRANT_HOST.")
    port: int = Field(
        default=6333, ge=1, le=65535, description="HTTP port. QDRANT_PORT."
    )
    grpc_port: int = Field(
        default=6334, ge=1, le=65535, description="gRPC port. QDRANT_GRPC_PORT."
    )
