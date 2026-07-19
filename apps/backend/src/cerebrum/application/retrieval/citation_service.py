"""``CitationService``: CIS Phase 3 Prompt 3's Citation Engine —
resolves each already-built
:class:`~cerebrum.application.semantic.hybrid_search_service.Citation`
(source document/version/chunk/entity/confidence/provenance — see that
class's docstring) into an :class:`EnrichedCitation` that also carries
the human-readable labels a citation display needs (document name,
version number, chunk position, entity name) — one extra, deliberately
narrow round-trip to PostgreSQL per unique document/chunk/entity
referenced (not per hit — see :meth:`CitationService.build_citations`'s
deduplication), since none of that is stored on the vector/search-index
payload the raw ``Citation`` is built from.
"""

import uuid
from dataclasses import dataclass
from typing import Any

from cerebrum.application.knowledge_graph.entity_service import EntityService
from cerebrum.application.retrieval.events import CitationGeneratedEvent
from cerebrum.application.semantic.hybrid_search_service import Citation, SearchHit
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.repositories.postgres.chunk_repository import ChunkRepository
from cerebrum.repositories.postgres.document_repository import DocumentRepository
from cerebrum.repositories.postgres.document_version_repository import (
    DocumentVersionRepository,
)
from cerebrum.shared.errors.exceptions import NotFoundException

_CitationKey = tuple[
    uuid.UUID | None, uuid.UUID | None, uuid.UUID | None, uuid.UUID | None
]


@dataclass(frozen=True, slots=True)
class EnrichedCitation:
    document_id: uuid.UUID | None
    document_version_id: uuid.UUID | None
    chunk_id: uuid.UUID | None
    entity_id: uuid.UUID | None
    confidence: float
    provenance: dict[str, Any]
    document_name: str | None
    version_number: int | None
    chunk_index: int | None
    entity_name: str | None


class CitationService:
    def __init__(
        self,
        *,
        document_repository: DocumentRepository,
        version_repository: DocumentVersionRepository,
        chunk_repository: ChunkRepository,
        entity_service: EntityService,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._documents = document_repository
        self._versions = version_repository
        self._chunks = chunk_repository
        self._entities = entity_service
        self._events = event_dispatcher

    async def build_citations(
        self, hits: list[SearchHit], *, workspace_id: uuid.UUID
    ) -> list[EnrichedCitation]:
        """Deduplicates by ``(document_id, document_version_id,
        chunk_id, entity_id)`` — the same underlying source cited by
        more than one hit (e.g. a chunk that is both a keyword and a
        vector hit) yields one citation, not two.
        """
        seen: dict[_CitationKey, EnrichedCitation] = {}
        for hit in hits:
            key = (
                hit.citation.document_id,
                hit.citation.document_version_id,
                hit.citation.chunk_id,
                hit.citation.entity_id,
            )
            if key in seen:
                continue
            seen[key] = await self._enrich(hit.citation, workspace_id=workspace_id)

        citations = list(seen.values())
        self._events.publish(
            CitationGeneratedEvent(
                workspace_id=workspace_id, citation_count=len(citations)
            )
        )
        return citations

    async def _enrich(
        self, citation: Citation, *, workspace_id: uuid.UUID
    ) -> EnrichedCitation:
        document_name = None
        if citation.document_id is not None:
            document = await self._documents.get_by_id(citation.document_id)
            document_name = document.name if document is not None else None

        version_number = None
        if citation.document_version_id is not None:
            version = await self._versions.get_by_id(citation.document_version_id)
            version_number = version.version_number if version is not None else None

        chunk_index = None
        if citation.chunk_id is not None:
            chunk = await self._chunks.get_by_id(citation.chunk_id)
            chunk_index = chunk.chunk_index if chunk is not None else None

        entity_name = None
        if citation.entity_id is not None:
            try:
                entity = await self._entities.get(
                    citation.entity_id, workspace_id=workspace_id
                )
                entity_name = entity.canonical_name
            except NotFoundException:
                entity_name = None

        return EnrichedCitation(
            document_id=citation.document_id,
            document_version_id=citation.document_version_id,
            chunk_id=citation.chunk_id,
            entity_id=citation.entity_id,
            confidence=citation.confidence,
            provenance=citation.provenance,
            document_name=document_name,
            version_number=version_number,
            chunk_index=chunk_index,
            entity_name=entity_name,
        )
