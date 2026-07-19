"""``ContextBuilderService``: CIS Phase 3 Prompt 3's Context Builder —
turns a flat list of
:class:`~cerebrum.application.semantic.hybrid_search_service.SearchHit`
(from
:class:`~cerebrum.application.retrieval.retrieval_service.RetrievalService`)
into a structured :class:`ContextPackage`: the full documents, chunks,
entities, and relationships those hits reference, resolved from
PostgreSQL (the system of record — hits themselves only carry IDs and a
snippet), plus a bounded graph-neighbor expansion and (optionally) each
document's version history.

Context Optimization (CIS Phase 3 Prompt 3's requirement) happens in
:meth:`ContextBuilderService.build`:

- **Deduplication** — chunks/entities are resolved into ``dict``s keyed
  by ID, so a source referenced by more than one hit (e.g. an entity
  that is both a keyword hit and cited by a chunk hit) appears once.
- **Chunk ordering** — resolved chunks are sorted by
  ``document_version_id`` then ``chunk_index``, restoring reading order
  rather than retrieval-rank order.
- **Entity grouping** — resolved entities are exposed both as a flat
  list and grouped by ``entity_type``.
- **Metadata enrichment** — hits only carry a ``title``/``snippet``;
  this service resolves the full ``Chunk``/``Entity``/``Document`` rows
  for their complete fields (entity ``description``, chunk
  ``chunk_index``/offsets, document ``name``).
- **Relationship expansion** — every
  :class:`~cerebrum.infrastructure.database.models.relationship.Relationship`
  connecting two *already-resolved* entities is included (not a fresh
  graph traversal — see ``graph_depth`` below for that), so a context
  package about "Alice and Bob" also carries the "Alice manages Bob"
  edge between them if one exists.
- **Compression** — resolved chunk text is concatenated up to
  ``max_characters``; ``truncated`` is set once any limit (chunk count,
  entity count, or character budget) is hit, so a caller building a
  downstream prompt (outside this milestone's scope — see Non-
  Objectives) knows the package is a bounded window, not the full
  retrieval result.

``graph_depth`` (default ``0``, disabled) additionally walks
:class:`~cerebrum.application.knowledge_graph.knowledge_graph_service.KnowledgeGraphService`'s
Neo4j-backed neighbor graph outward from every resolved entity —
configurable-depth support per this milestone's requirement — kept
separate from relationship expansion above because it can reach
entities *not* already in the context package (a true graph walk, not
just "connect what's already here").
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from cerebrum.application.knowledge_graph.entity_service import EntityService
from cerebrum.application.knowledge_graph.knowledge_graph_service import (
    KnowledgeGraphService,
)
from cerebrum.application.knowledge_graph.relationship_service import (
    RelationshipService,
)
from cerebrum.application.retrieval.events import ContextBuiltEvent
from cerebrum.application.semantic.hybrid_search_service import Citation, SearchHit
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.chunk import Chunk
from cerebrum.infrastructure.database.models.entity import Entity
from cerebrum.repositories.contracts import Pagination
from cerebrum.repositories.postgres.chunk_repository import ChunkRepository
from cerebrum.repositories.postgres.document_repository import DocumentRepository
from cerebrum.repositories.postgres.document_version_repository import (
    DocumentVersionRepository,
)
from cerebrum.shared.errors.exceptions import NotFoundException

_DEFAULT_MAX_CHUNKS = 20
_DEFAULT_MAX_ENTITIES = 20
_DEFAULT_MAX_CHARACTERS = 8000


@dataclass(frozen=True, slots=True)
class ContextDocument:
    document_id: uuid.UUID
    name: str
    version_id: uuid.UUID | None
    version_number: int | None


@dataclass(frozen=True, slots=True)
class ContextChunk:
    chunk_id: uuid.UUID
    document_version_id: uuid.UUID
    chunk_index: int
    text: str
    citation: Citation


@dataclass(frozen=True, slots=True)
class ContextEntity:
    entity_id: uuid.UUID
    entity_type: str
    canonical_name: str
    description: str | None
    confidence: float
    citation: Citation


@dataclass(frozen=True, slots=True)
class ContextRelationship:
    relationship_id: uuid.UUID
    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    relationship_type: str
    confidence: float


@dataclass(frozen=True, slots=True)
class VersionHistoryEntry:
    document_id: uuid.UUID
    version_id: uuid.UUID
    version_number: int
    is_current: bool


@dataclass(frozen=True, slots=True)
class ContextPackage:
    query_text: str | None
    documents: list[ContextDocument]
    chunks: list[ContextChunk]
    entities: list[ContextEntity]
    entities_by_type: dict[str, list[ContextEntity]]
    relationships: list[ContextRelationship]
    graph_neighbors: dict[str, list[dict[str, Any]]]
    version_history: list[VersionHistoryEntry]
    citations: list[Citation] = field(default_factory=list)
    truncated: bool = False


class ContextBuilderService:
    def __init__(
        self,
        *,
        chunk_repository: ChunkRepository,
        entity_service: EntityService,
        relationship_service: RelationshipService,
        document_repository: DocumentRepository,
        version_repository: DocumentVersionRepository,
        knowledge_graph_service: KnowledgeGraphService,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._chunks = chunk_repository
        self._entities = entity_service
        self._relationships = relationship_service
        self._documents = document_repository
        self._versions = version_repository
        self._graph = knowledge_graph_service
        self._events = event_dispatcher

    async def build(
        self,
        hits: list[SearchHit],
        *,
        workspace_id: uuid.UUID,
        query_text: str | None = None,
        max_chunks: int = _DEFAULT_MAX_CHUNKS,
        max_entities: int = _DEFAULT_MAX_ENTITIES,
        max_characters: int = _DEFAULT_MAX_CHARACTERS,
        graph_depth: int = 0,
        include_version_history: bool = False,
    ) -> ContextPackage:
        truncated = False

        chunk_ids = _unique_uuids(
            hit.citation.chunk_id for hit in hits if hit.citation.chunk_id is not None
        )
        entity_ids = _unique_uuids(
            hit.citation.entity_id for hit in hits if hit.citation.entity_id is not None
        )
        citation_by_chunk = {
            hit.citation.chunk_id: hit.citation
            for hit in hits
            if hit.citation.chunk_id is not None
        }
        citation_by_entity = {
            hit.citation.entity_id: hit.citation
            for hit in hits
            if hit.citation.entity_id is not None
        }

        if len(chunk_ids) > max_chunks:
            chunk_ids = chunk_ids[:max_chunks]
            truncated = True
        if len(entity_ids) > max_entities:
            entity_ids = entity_ids[:max_entities]
            truncated = True

        chunks, chunks_truncated = await self._resolve_chunks(
            chunk_ids, citation_by_chunk, max_characters=max_characters
        )
        truncated = truncated or chunks_truncated

        entities = await self._resolve_entities(
            entity_ids, citation_by_entity, workspace_id=workspace_id
        )
        entities_by_type: dict[str, list[ContextEntity]] = {}
        for context_entity in entities:
            entities_by_type.setdefault(context_entity.entity_type, []).append(
                context_entity
            )

        relationships = await self._expand_relationships(
            entities, workspace_id=workspace_id
        )

        document_ids = _unique_uuids(
            hit.citation.document_id
            for hit in hits
            if hit.citation.document_id is not None
        )
        documents = await self._resolve_documents(document_ids)

        graph_neighbors: dict[str, list[dict[str, Any]]] = {}
        if graph_depth > 0:
            for context_entity in entities:
                neighbors = await self._graph.get_neighbors(
                    context_entity.entity_id,
                    workspace_id=workspace_id,
                    depth=graph_depth,
                )
                graph_neighbors[str(context_entity.entity_id)] = neighbors

        version_history: list[VersionHistoryEntry] = []
        if include_version_history:
            for document_id in document_ids:
                version_history.extend(await self._resolve_version_history(document_id))

        citations = [chunk.citation for chunk in chunks] + [
            entity.citation for entity in entities
        ]

        package = ContextPackage(
            query_text=query_text,
            documents=documents,
            chunks=chunks,
            entities=entities,
            entities_by_type=entities_by_type,
            relationships=relationships,
            graph_neighbors=graph_neighbors,
            version_history=version_history,
            citations=citations,
            truncated=truncated,
        )
        self._events.publish(
            ContextBuiltEvent(
                workspace_id=workspace_id,
                document_count=len(documents),
                chunk_count=len(chunks),
                entity_count=len(entities),
                truncated=truncated,
            )
        )
        return package

    async def _resolve_chunks(
        self,
        chunk_ids: list[uuid.UUID],
        citation_by_chunk: dict[uuid.UUID, Citation],
        *,
        max_characters: int,
    ) -> tuple[list[ContextChunk], bool]:
        resolved: list[Chunk] = []
        for chunk_id in chunk_ids:
            chunk = await self._chunks.get_by_id(chunk_id)
            if chunk is not None:
                resolved.append(chunk)
        resolved.sort(key=lambda c: (str(c.document_version_id), c.chunk_index))

        context_chunks = []
        budget = max_characters
        truncated = False
        for chunk in resolved:
            if budget <= 0:
                truncated = True
                break
            text = chunk.text
            if len(text) > budget:
                text = text[:budget]
                truncated = True
            budget -= len(text)
            context_chunks.append(
                ContextChunk(
                    chunk_id=chunk.id,
                    document_version_id=chunk.document_version_id,
                    chunk_index=chunk.chunk_index,
                    text=text,
                    citation=citation_by_chunk.get(
                        chunk.id,
                        Citation(
                            document_id=None,
                            document_version_id=chunk.document_version_id,
                            chunk_id=chunk.id,
                            entity_id=None,
                            confidence=1.0,
                            provenance={},
                        ),
                    ),
                )
            )
        return context_chunks, truncated

    async def _resolve_entities(
        self,
        entity_ids: list[uuid.UUID],
        citation_by_entity: dict[uuid.UUID, Citation],
        *,
        workspace_id: uuid.UUID,
    ) -> list[ContextEntity]:
        context_entities = []
        for entity_id in entity_ids:
            entity: Entity | None
            try:
                entity = await self._entities.get(entity_id, workspace_id=workspace_id)
            except NotFoundException:
                continue
            context_entities.append(
                ContextEntity(
                    entity_id=entity.id,
                    entity_type=entity.entity_type,
                    canonical_name=entity.canonical_name,
                    description=entity.description,
                    confidence=entity.confidence,
                    citation=citation_by_entity.get(
                        entity.id,
                        Citation(
                            document_id=entity.source_document_id,
                            document_version_id=None,
                            chunk_id=entity.source_chunk_id,
                            entity_id=entity.id,
                            confidence=entity.confidence,
                            provenance={},
                        ),
                    ),
                )
            )
        context_entities.sort(key=lambda e: (e.entity_type, e.canonical_name))
        return context_entities

    async def _expand_relationships(
        self, entities: list[ContextEntity], *, workspace_id: uuid.UUID
    ) -> list[ContextRelationship]:
        entity_ids = {entity.entity_id for entity in entities}
        if not entity_ids:
            return []
        seen: dict[uuid.UUID, ContextRelationship] = {}
        for entity_id in entity_ids:
            for relationship in await self._relationships.list_for_entity(
                entity_id, workspace_id=workspace_id
            ):
                if (
                    relationship.source_entity_id in entity_ids
                    and relationship.target_entity_id in entity_ids
                    and relationship.id not in seen
                ):
                    seen[relationship.id] = ContextRelationship(
                        relationship_id=relationship.id,
                        source_entity_id=relationship.source_entity_id,
                        target_entity_id=relationship.target_entity_id,
                        relationship_type=relationship.relationship_type,
                        confidence=relationship.confidence,
                    )
        return list(seen.values())

    async def _resolve_documents(
        self, document_ids: list[uuid.UUID]
    ) -> list[ContextDocument]:
        documents = []
        for document_id in document_ids:
            document = await self._documents.get_by_id(document_id)
            if document is None:
                continue
            current_version = await self._versions.get_current(document_id)
            documents.append(
                ContextDocument(
                    document_id=document.id,
                    name=document.name,
                    version_id=current_version.id if current_version else None,
                    version_number=(
                        current_version.version_number if current_version else None
                    ),
                )
            )
        return documents

    async def _resolve_version_history(
        self, document_id: uuid.UUID
    ) -> list[VersionHistoryEntry]:
        page = await self._versions.list_by_document(
            document_id, pagination=Pagination(page=1, page_size=100)
        )
        return [
            VersionHistoryEntry(
                document_id=document_id,
                version_id=version.id,
                version_number=version.version_number,
                is_current=version.is_current,
            )
            for version in page.items
        ]


def _unique_uuids(values: Any) -> list[uuid.UUID]:
    seen: dict[uuid.UUID, None] = {}
    for value in values:
        if value not in seen:
            seen[value] = None
    return list(seen.keys())
