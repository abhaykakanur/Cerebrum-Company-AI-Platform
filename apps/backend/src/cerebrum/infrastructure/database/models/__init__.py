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
from cerebrum.infrastructure.database.models.capsule import EmployeeKnowledgeCapsule
from cerebrum.infrastructure.database.models.capsule_evidence import (
    CapsuleEvidenceRecord,
)
from cerebrum.infrastructure.database.models.capsule_timeline_event import (
    CapsuleTimelineEvent,
)
from cerebrum.infrastructure.database.models.chunk import Chunk, ChunkingStrategy
from cerebrum.infrastructure.database.models.collection import (
    Collection,
    CollectionDocument,
)
from cerebrum.infrastructure.database.models.connector import (
    Connector,
    ConnectorAuthType,
    ConnectorHealthStatus,
    ConnectorStatus,
    ConnectorType,
)
from cerebrum.infrastructure.database.models.connector_sync_mapping import (
    ConnectorSyncMapping,
    MappingSyncStatus,
)
from cerebrum.infrastructure.database.models.connector_sync_run import (
    ConnectorSyncRun,
    SyncRunStatus,
    SyncType,
)
from cerebrum.infrastructure.database.models.conversation import (
    Conversation,
    ConversationStatus,
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
from cerebrum.infrastructure.database.models.entity import Entity, EntityType
from cerebrum.infrastructure.database.models.folder import Folder
from cerebrum.infrastructure.database.models.label import DocumentLabel, Label
from cerebrum.infrastructure.database.models.membership import WorkspaceMembership
from cerebrum.infrastructure.database.models.message import Message, MessageRole
from cerebrum.infrastructure.database.models.organization import Organization
from cerebrum.infrastructure.database.models.processing_job import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
)
from cerebrum.infrastructure.database.models.relationship import (
    Relationship,
    RelationshipType,
)
from cerebrum.infrastructure.database.models.role import (
    Permission,
    Role,
    RolePermission,
)
from cerebrum.infrastructure.database.models.session import UserSession
from cerebrum.infrastructure.database.models.tag import DocumentTag, Tag
from cerebrum.infrastructure.database.models.user import User
from cerebrum.infrastructure.database.models.workflow import Workflow, WorkflowStatus
from cerebrum.infrastructure.database.models.workflow_run import (
    WorkflowRun,
    WorkflowRunStatus,
)
from cerebrum.infrastructure.database.models.workflow_schedule import (
    ScheduleStatus,
    ScheduleType,
    WorkflowSchedule,
)
from cerebrum.infrastructure.database.models.workflow_step_run import (
    WorkflowStepRun,
    WorkflowStepRunStatus,
)
from cerebrum.infrastructure.database.models.workflow_version import (
    StepType,
    TriggerType,
    WorkflowVersion,
)
from cerebrum.infrastructure.database.models.workspace import Workspace

__all__ = [
    "APIKey",
    "AuditEvent",
    "AuditEventType",
    "CapsuleEvidenceRecord",
    "CapsuleTimelineEvent",
    "Chunk",
    "ChunkingStrategy",
    "Collection",
    "CollectionDocument",
    "Connector",
    "ConnectorAuthType",
    "ConnectorHealthStatus",
    "ConnectorStatus",
    "ConnectorSyncMapping",
    "ConnectorSyncRun",
    "ConnectorType",
    "Conversation",
    "ConversationStatus",
    "Document",
    "DocumentExtraction",
    "DocumentLabel",
    "DocumentManifest",
    "DocumentMetadata",
    "DocumentStatus",
    "DocumentTag",
    "DocumentVersion",
    "EmployeeKnowledgeCapsule",
    "Entity",
    "EntityType",
    "ExtractionStatus",
    "Folder",
    "Label",
    "ManifestStatus",
    "MappingSyncStatus",
    "Message",
    "MessageRole",
    "Organization",
    "Permission",
    "ProcessingJob",
    "ProcessingJobStatus",
    "ProcessingJobType",
    "QuarantineStatus",
    "Relationship",
    "RelationshipType",
    "Role",
    "RolePermission",
    "ScheduleStatus",
    "ScheduleType",
    "StepType",
    "SyncRunStatus",
    "SyncType",
    "Tag",
    "TriggerType",
    "UploadStatus",
    "UserSession",
    "User",
    "VersionType",
    "Workflow",
    "WorkflowRun",
    "WorkflowRunStatus",
    "WorkflowSchedule",
    "WorkflowStatus",
    "WorkflowStepRun",
    "WorkflowStepRunStatus",
    "WorkflowVersion",
    "Workspace",
    "WorkspaceMembership",
]
