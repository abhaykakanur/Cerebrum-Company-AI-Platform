"""MinIO (S3-compatible object storage) connection configuration.

Owns the ``MINIO_*`` environment variables defined in `.env.example`.
See docs/architecture/specification/42_Database_Responsibilities.md for
MinIO's role as the authoritative object-storage datastore.
"""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class MinIOSettings(BaseSettings):
    """Connection parameters for the object-storage datastore."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="MINIO_",
        extra="ignore",
    )

    endpoint: str = Field(default="localhost:9000", description="MINIO_ENDPOINT.")
    api_port: int = Field(default=9000, ge=1, le=65535, description="MINIO_API_PORT.")
    console_port: int = Field(
        default=9001, ge=1, le=65535, description="MINIO_CONSOLE_PORT."
    )
    access_key: str = Field(
        default="changeme-local-only", description="MINIO_ACCESS_KEY."
    )
    secret_key: SecretStr = Field(
        default=SecretStr("changeme-local-only"), description="MINIO_SECRET_KEY."
    )
    bucket: str = Field(default="cerebrum-documents", description="MINIO_BUCKET.")
    secure: bool = Field(
        default=False,
        description="Use HTTPS. False by default — local Docker Compose MinIO "
        "(infrastructure/docker/) serves plain HTTP; production deployments "
        "override via MINIO_SECURE=true. MINIO_SECURE.",
    )
