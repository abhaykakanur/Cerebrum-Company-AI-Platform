"""OpenSearch connection configuration.

Owns the ``OPENSEARCH_*`` environment variables defined in
`.env.example`. See docs/architecture/specification/65_Search_Architecture.md
for OpenSearch's role in the hybrid search pipeline.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from cerebrum.config import ENV_FILE


class OpenSearchSettings(BaseSettings):
    """Connection parameters for the keyword/hybrid search datastore."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_prefix="OPENSEARCH_",
        extra="ignore",
    )

    host: str = Field(default="localhost", description="OPENSEARCH_HOST.")
    port: int = Field(default=9200, ge=1, le=65535, description="OPENSEARCH_PORT.")
    perf_port: int = Field(
        default=9600,
        ge=1,
        le=65535,
        description="Performance Analyzer port. OPENSEARCH_PERF_PORT.",
    )
