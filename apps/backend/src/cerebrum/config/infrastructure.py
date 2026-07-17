"""Connection-lifecycle policy shared by every infrastructure client
manager: how many times to retry an initial connection attempt, how long
to back off between attempts, and how long to wait before giving up on a
single attempt.

Owns the ``INFRA_*`` environment variables. Deliberately centralized —
per CIS Phase 1 Prompt 4's "no duplicated code" quality standard, retry
tuning is a policy every infrastructure/ client manager (PostgreSQL,
Redis, Neo4j, Qdrant, MinIO, OpenSearch) shares rather than each
re-declaring its own retry/backoff fields.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class InfrastructureSettings(BaseSettings):
    """Retry and timeout policy for infrastructure client connection
    attempts at startup — see cerebrum.infrastructure.retry.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="INFRA_",
        extra="ignore",
    )

    connect_retries: int = Field(
        default=3,
        ge=0,
        description="Additional attempts after the first, per client, before "
        "giving up and reporting that client unavailable. INFRA_CONNECT_RETRIES.",
    )
    connect_retry_backoff_seconds: float = Field(
        default=0.5,
        ge=0.0,
        description="Base delay before the first retry; doubles each subsequent "
        "attempt (exponential backoff). INFRA_CONNECT_RETRY_BACKOFF_SECONDS.",
    )
    connect_timeout_seconds: float = Field(
        default=5.0,
        gt=0.0,
        description="Per-attempt connection timeout passed to each driver where "
        "supported. INFRA_CONNECT_TIMEOUT_SECONDS.",
    )
