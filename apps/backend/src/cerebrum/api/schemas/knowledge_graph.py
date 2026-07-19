"""Request/response schemas for CIS Phase 3 Prompt 1's Knowledge Graph
& Entity Intelligence API. Every response model inherits
:class:`~cerebrum.api.schemas.base.APIModel` (``from_attributes=True``)
so a route can return ``XResponse.model_validate(orm_object)`` directly
— see cerebrum.api.schemas.knowledge's identical docstring precedent.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from cerebrum.api.schemas.base import APIModel
from cerebrum.infrastructure.database.models.entity import EntityType
from cerebrum.infrastructure.database.models.relationship import RelationshipType

# --- Entity -------------------------------------------------------------------


class EntityResponse(APIModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    organization_id: uuid.UUID
    entity_type: EntityType
    custom_type_name: str | None
    canonical_name: str
    aliases: list[str]
    description: str | None
    confidence: float
    source_chunk_id: uuid.UUID | None
    source_document_id: uuid.UUID | None
    provenance: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class EntityCreateRequest(APIModel):
    entity_type: EntityType
    canonical_name: str = Field(min_length=1, max_length=500)
    custom_type_name: str | None = Field(default=None, max_length=100)
    aliases: list[str] = Field(default_factory=list)
    description: str | None = Field(default=None, max_length=2000)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class EntityUpdateRequest(APIModel):
    canonical_name: str | None = Field(default=None, min_length=1, max_length=500)
    aliases: list[str] | None = None
    description: str | None = Field(default=None, max_length=2000)


class EntityHistoryResponse(APIModel):
    provenance: list[dict[str, Any]]


# --- Relationship ---------------------------------------------------------------


class RelationshipResponse(APIModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    organization_id: uuid.UUID
    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    relationship_type: RelationshipType
    custom_type_name: str | None
    confidence: float
    evidence: str | None
    source_chunk_id: uuid.UUID | None
    source_document_id: uuid.UUID | None
    valid_from: datetime | None
    valid_to: datetime | None
    created_at: datetime
    updated_at: datetime


class RelationshipCreateRequest(APIModel):
    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    relationship_type: RelationshipType
    custom_type_name: str | None = Field(default=None, max_length=100)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence: str | None = Field(default=None, max_length=2000)


class RelationshipUpdateRequest(APIModel):
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence: str | None = Field(default=None, max_length=2000)


# --- Graph ------------------------------------------------------------------


class GraphNodeResponse(APIModel):
    """A Neo4j node's own (denormalized) properties — see
    cerebrum.repositories.neo4j.knowledge_graph_repository.KnowledgeGraphRepository.upsert_entity_node
    for exactly which ones it writes. Distinct from
    :class:`EntityResponse` (the full PostgreSQL row): a graph query
    result only carries what was mirrored into the graph.
    """

    id: str
    workspace_id: str
    entity_type: str
    canonical_name: str
    aliases: list[str]
    confidence: float


class GraphStatisticsResponse(APIModel):
    entity_count: int
    relationship_count: int


class GraphConsistencyResponse(APIModel):
    is_consistent: bool
    issues: list[str]


class ProcessGraphResponse(APIModel):
    entity_count: int
    relationship_count: int
