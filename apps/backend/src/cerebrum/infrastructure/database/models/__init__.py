"""Foundational ORM models for the Identity & Security platform (CIS
Phase 1 Prompt 5) plus the Knowledge Domain's business entities (CIS
Phase 2 Prompts 1-2) — one module each, in this package.

Phase 1's models are deliberately minimal — "No business profile data"
(CIS Phase 1 Prompt 5's scope): no name/avatar/bio/preferences on
``User``, no seeded business permissions. Phase 2's models are the first
real business domain: ``Folder``, ``Document``, ``DocumentVersion``,
``DocumentMetadata``, ``Tag``, ``Label``, ``Collection``,
``ProcessingJob``, and their association tables.

Every model is imported here so
``cerebrum.infrastructure.database.base.Base.metadata`` sees all of them
— Alembic's ``env.py`` imports ``Base``, not this package, but a model
defined and never imported anywhere is invisible to
``Base.metadata.create_all``/autogenerate, so this import is load-bearing.
"""

from cerebrum.infrastructure.database.models.api_key import APIKey
from cerebrum.infrastructure.database.models.audit import AuditEvent, AuditEventType
from cerebrum.infrastructure.database.models.chunk import Chunk, ChunkingStrategy
from cerebrum.infrastructure.database.models.collection import (
    Collection,
    CollectionDocument,
)
from cerebrum.infrastructure.database.models.document import Document, DocumentStatus
from cerebrum.infrastructure.database.models.document_extraction import (
    DocumentExtraction,
    ExtractionStatus,
)
from cerebrum.infrastructure.database.models.document_manifest import (
    DocumentManifest,
    ManifestStatus,
)
from cerebrum.infrastructure.database.models.document_metadata import (
    DocumentMetadata,
    QuarantineStatus,
)
from cerebrum.infrastructure.database.models.document_version import (
    DocumentVersion,
    UploadStatus,
    VersionType,
)
from cerebrum.infrastructure.database.models.folder import Folder
from cerebrum.infrastructure.database.models.label import DocumentLabel, Label
from cerebrum.infrastructure.database.models.membership import WorkspaceMembership
from cerebrum.infrastructure.database.models.organization import Organization
from cerebrum.infrastructure.database.models.processing_job import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
)
from cerebrum.infrastructure.database.models.role import (
    Permission,
    Role,
    RolePermission,
)
from cerebrum.infrastructure.database.models.session import UserSession
from cerebrum.infrastructure.database.models.tag import DocumentTag, Tag
from cerebrum.infrastructure.database.models.user import User
from cerebrum.infrastructure.database.models.workspace import Workspace

__all__ = [
    "APIKey",
    "AuditEvent",
    "AuditEventType",
    "Chunk",
    "ChunkingStrategy",
    "Collection",
    "CollectionDocument",
    "Document",
    "DocumentExtraction",
    "DocumentLabel",
    "DocumentManifest",
    "DocumentMetadata",
    "DocumentStatus",
    "DocumentTag",
    "DocumentVersion",
    "ExtractionStatus",
    "Folder",
    "Label",
    "ManifestStatus",
    "Organization",
    "Permission",
    "ProcessingJob",
    "ProcessingJobStatus",
    "ProcessingJobType",
    "QuarantineStatus",
    "Role",
    "RolePermission",
    "Tag",
    "UploadStatus",
    "UserSession",
    "User",
    "VersionType",
    "Workspace",
    "WorkspaceMembership",
]
