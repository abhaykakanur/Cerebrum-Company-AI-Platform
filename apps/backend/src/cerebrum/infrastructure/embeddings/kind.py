"""The five embeddable artifact kinds CIS Phase 3 Prompt 2 names —
shared by cerebrum.repositories.qdrant.vector_repository (the ``kind``
payload field distinguishing points within one collection) and
cerebrum.repositories.opensearch.search_index_repository (same
convention, one index).
"""

from enum import StrEnum


class EmbeddingKind(StrEnum):
    CHUNK = "chunk"
    ENTITY_DESCRIPTION = "entity_description"
    RELATIONSHIP_DESCRIPTION = "relationship_description"
    DOCUMENT_SUMMARY = "document_summary"
    METADATA = "metadata"
