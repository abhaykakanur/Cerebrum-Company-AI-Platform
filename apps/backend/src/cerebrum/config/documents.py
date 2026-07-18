"""Document upload validation configuration — CIS Phase 2 Prompt 1's
Maximum File Size / MIME Type validation requirements, made
environment-configurable rather than hard-coded in
cerebrum.application.knowledge.document_service.
"""

from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class DocumentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="DOCUMENT_",
        extra="ignore",
    )

    max_file_size_bytes: int = Field(
        default=100 * 1024 * 1024,
        gt=0,
        description="Hard ceiling for a single document version's binary content. "
        "DOCUMENT_MAX_FILE_SIZE_BYTES.",
    )
    allowed_mime_types: Annotated[list[str], NoDecode] = Field(
        default_factory=list,
        description="Allowed MIME types for document uploads, comma-separated. "
        "Empty (the default) means any MIME type is accepted. "
        "DOCUMENT_ALLOWED_MIME_TYPES.",
    )

    @property
    def allowed_mime_types_or_none(self) -> frozenset[str] | None:
        """Adapts the empty-list-means-any convention above onto
        :attr:`~cerebrum.infrastructure.storage.files.FileValidationPolicy.allowed_content_types`'s
        ``None``-means-any convention.
        """
        return frozenset(self.allowed_mime_types) if self.allowed_mime_types else None
