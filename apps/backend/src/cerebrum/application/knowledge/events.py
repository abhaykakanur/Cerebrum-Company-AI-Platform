"""Concrete domain events the Knowledge Domain raises — the first real
subclasses of cerebrum.events.base.DomainEvent (previously only the
base contract; see that module's docstring). CIS Phase 2 Prompt 4's
Event Emission requirement: this is the emission side only — nothing in
this codebase subscribes to :class:`DocumentKnowledgePreparedEvent` yet,
per that milestone's own framing ("events... consumed in Phase 3", which
this codebase has not reached).
"""

import uuid
from dataclasses import dataclass

from cerebrum.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentKnowledgePreparedEvent(DomainEvent):
    """Raised once by
    cerebrum.application.knowledge.knowledge_preparation_service.KnowledgePreparationService.prepare
    after a document version's extraction and chunking both complete
    successfully — the signal a future Phase 3 embedding/indexing
    pipeline would subscribe to.
    """

    event_type: str = "knowledge.document_prepared"
    document_version_id: uuid.UUID
    workspace_id: uuid.UUID
    chunk_count: int
    chunking_strategy: str
