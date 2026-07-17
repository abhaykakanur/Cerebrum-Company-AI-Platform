"""Background-processing runtime configuration.

Placeholder settings only — no worker is started at this milestone (see
cerebrum.workers, which defines interfaces only). Defined now so the
typed-configuration surface for the Background Processing Layer
(docs/architecture/specification/36_Background_Processing.md) exists
before its first concrete worker is registered in a later phase.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    """Background-runtime sizing. Not consumed by any running process yet."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="WORKER_",
        extra="ignore",
    )

    concurrency: int = Field(
        default=4,
        ge=1,
        description="Max concurrent background tasks. WORKER_CONCURRENCY.",
    )
    enabled: bool = Field(
        default=False,
        description="Whether the background runtime starts at all. False at this "
        "milestone — see cerebrum.core.background. WORKER_ENABLED.",
    )
