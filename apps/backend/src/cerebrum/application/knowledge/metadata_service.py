"""``MetadataService``: read access to
:class:`~cerebrum.infrastructure.database.models.document_metadata.DocumentMetadata`
— CIS Phase 2 Prompt 1's Metadata Management. Creation happens inside
cerebrum.application.knowledge.version_service.VersionService.create_version
(metadata and its owning version are created together, atomically); this
service is the read-side surface a route depends on instead of reaching
into the repository directly.
"""

import uuid

from cerebrum.infrastructure.database.models.document_metadata import (
    DocumentMetadata,
)
from cerebrum.repositories.postgres.document_metadata_repository import (
    DocumentMetadataRepository,
)
from cerebrum.repositories.postgres.document_version_repository import (
    DocumentVersionRepository,
)
from cerebrum.shared.errors.exceptions import NotFoundException


class MetadataService:
    def __init__(
        self,
        *,
        metadata_repository: DocumentMetadataRepository,
        version_repository: DocumentVersionRepository,
    ) -> None:
        self._metadata = metadata_repository
        self._versions = version_repository

    async def get_for_version(self, document_version_id: uuid.UUID) -> DocumentMetadata:
        version = await self._versions.get_by_id(document_version_id)
        if version is None:
            raise NotFoundException(
                f"No document version with id {document_version_id}."
            )
        metadata = await self._metadata.get_by_version(document_version_id)
        if metadata is None:
            raise NotFoundException(
                f"No metadata recorded for document version {document_version_id}."
            )
        return metadata
