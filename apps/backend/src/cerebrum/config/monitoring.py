"""Observability toggle configuration.

Placeholder settings only — no metrics/tracing backend is wired at this
milestone (see cerebrum.core.observability's no-op implementations).
Defined now so a future Prometheus/OpenTelemetry adapter has a settled
place to read its enablement flag from, per
docs/architecture/specification/38_Observability.md.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from cerebrum.config import ENV_FILE


class MonitoringSettings(BaseSettings):
    """Whether observability integrations are active. Both default to
    False — enabling either without a real backend configured would
    silently no-op, which is correct today but must be an explicit,
    intentional choice once real backends exist.
    """

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_prefix="MONITORING_",
        extra="ignore",
    )

    metrics_enabled: bool = Field(
        default=False, description="MONITORING_METRICS_ENABLED."
    )
    tracing_enabled: bool = Field(
        default=False, description="MONITORING_TRACING_ENABLED."
    )
