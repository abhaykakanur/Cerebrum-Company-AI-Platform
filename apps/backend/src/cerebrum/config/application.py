"""Application-identity configuration: which environment this process is
running as, and the metadata describing the application itself.

See docs/architecture/specification/37_Configuration_Strategy.md's
Environment Variables category — this module owns the ``ENVIRONMENT``
variable, the only environment variable without a subsystem prefix.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from cerebrum.config.environment import Environment


class ApplicationSettings(BaseSettings):
    """Identity and lifecycle metadata for the running process."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Deployment mode. Read from ENVIRONMENT.",
    )
    name: str = Field(default="Cerebrum", description="Application display name.")
    version: str = Field(
        default="0.1.0",
        description="Application version, surfaced in API metadata and health "
        "responses.",
    )
    build_commit: str = Field(
        default="unknown",
        description="Git commit SHA this build was produced from — set by the "
        "CI/Docker build (see apps/backend/Dockerfile's BUILD_COMMIT arg), "
        "surfaced on GET /health for deployment verification. 'unknown' for a "
        "local development run. BUILD_COMMIT.",
    )
    build_time: str = Field(
        default="local",
        description="ISO-8601 UTC build timestamp — set by the CI/Docker build. "
        "'local' for a local development run. BUILD_TIME.",
    )

    @property
    def debug(self) -> bool:
        """Debug affordances (verbose error detail, interactive docs) are
        derived from environment, never set independently — see
        docs/architecture/specification/37_Configuration_Strategy.md's
        Environment-Variables-drive-deployment-topology principle.
        """
        return not self.environment.is_production_like
