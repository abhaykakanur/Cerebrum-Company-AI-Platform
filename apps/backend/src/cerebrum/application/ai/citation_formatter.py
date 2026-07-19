"""``CitationFormatter``: CIS Phase 4 Prompt 1's citation-formatting
service — the one place that turns an
:class:`~cerebrum.application.retrieval.citation_service.EnrichedCitation`
into text, in either of two directions:

- **Into the prompt** (:meth:`assign_markers`/:meth:`format_reference_line`)
  — a stable ``[1]``, ``[2]``, ... marker per citation, and a one-line
  human-readable reference the system prompt instructs the model to
  cite by marker rather than restating.
- **Out of the model's response** (consumed by
  cerebrum.application.ai.ai_response_service.AIResponseService's
  citation verification) — the same marker->citation mapping lets a
  response's citation list be reduced to only the sources the model's
  own text actually referenced.
"""

from cerebrum.application.retrieval.citation_service import EnrichedCitation


class CitationFormatter:
    @staticmethod
    def marker(index: int) -> str:
        return f"[{index}]"

    @classmethod
    def assign_markers(
        cls, citations: list[EnrichedCitation]
    ) -> dict[str, EnrichedCitation]:
        """A stable marker per citation, in the given (already-ranked)
        order — ``{"[1]": citations[0], "[2]": citations[1], ...}``.
        """
        return {cls.marker(i + 1): citation for i, citation in enumerate(citations)}

    @staticmethod
    def format_reference_line(marker: str, citation: EnrichedCitation) -> str:
        return f"{marker} {CitationFormatter.label(citation)}"

    @staticmethod
    def label(citation: EnrichedCitation) -> str:
        parts: list[str] = []
        if citation.document_name:
            parts.append(citation.document_name)
        if citation.version_number is not None:
            parts.append(f"version {citation.version_number}")
        if citation.chunk_index is not None:
            parts.append(f"chunk {citation.chunk_index}")
        if citation.entity_name:
            parts.append(f"entity: {citation.entity_name}")
        if not parts:
            parts.append("unattributed source")
        return f"{', '.join(parts)} (confidence: {citation.confidence:.2f})"
