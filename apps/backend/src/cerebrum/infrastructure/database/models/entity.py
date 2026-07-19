"""``Entity``: a canonical, deduplicated knowledge-graph node extracted
from processed document chunks — CIS Phase 3 Prompt 1's Knowledge Graph
& Entity Intelligence. The system of record for entity attributes,
tenant scoping, audit, and soft delete; the corresponding Neo4j node
(see cerebrum.repositories.neo4j.knowledge_graph_repository) is a graph
projection of this row, kept in sync by
cerebrum.application.knowledge_graph.knowledge_graph_service.KnowledgeGraphService
— never written to directly by anything else, mirroring
cerebrum.infrastructure.database.models.document_metadata's "one
authoritative store, one synchronized projection" shape (there:
MinIO/PostgreSQL; here: PostgreSQL/Neo4j).
"""

import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    AuditFieldsMixin,
    OptimisticLockMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class EntityType(StrEnum):
    """The fourteen named types CIS Phase 3 Prompt 1 lists, plus
    ``CUSTOM`` for a caller-defined type (see ``Entity.custom_type_name``).
    """

    PERSON = "person"
    ORGANIZATION = "organization"
    TEAM = "team"
    PROJECT = "project"
    TECHNOLOGY = "technology"
    PRODUCT = "product"
    CUSTOMER = "customer"
    DOCUMENT = "document"
    MEETING = "meeting"
    DECISION = "decision"
    POLICY = "policy"
    PROCEDURE = "procedure"
    LOCATION = "location"
    DATE = "date"
    CUSTOM = "custom"


class Entity(
    Base,
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    SoftDeleteMixin,
    AuditFieldsMixin,
    OptimisticLockMixin,
):
    __tablename__ = "entities"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    """Denormalized off ``workspace_id`` — same "Tenant" field CIS Phase
    3 Prompt 1 lists separately from "Workspace" — see
    cerebrum.infrastructure.database.models.audit.AuditEvent for the
    same pattern (``organization_id`` alongside ``workspace_id``, not
    derived via a join on every query).
    """
    entity_type: Mapped[str] = mapped_column(String(30), index=True)
    custom_type_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    """Populated only when ``entity_type == EntityType.CUSTOM`` — the
    caller-defined type name; see
    cerebrum.infrastructure.entities.extractors for how a configurable
    extractor produces one.
    """
    canonical_name: Mapped[str] = mapped_column(String(500), index=True)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    """0.0-1.0 — see
    cerebrum.infrastructure.entities.results.ExtractedEntity's docstring
    for how an extractor computes one; a manually-created entity (via
    the API, not the pipeline) defaults to full confidence.
    """
    source_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    provenance: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    """An accumulating list of contribution records — one per extraction
    run that touched this entity (``{"document_version_id", "chunk_id",
    "confidence", "extractor", "extracted_at"}``) — CIS Phase 3 Prompt
    1's required "Provenance" field, and what
    cerebrum.api.v1.entities's Entity History endpoint reads; not a
    single dict, since a deduplicated entity is, by definition, backed
    by more than one extraction over its lifetime.
    """
