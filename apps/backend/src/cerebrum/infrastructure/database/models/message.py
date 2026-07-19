"""``Message``: one turn of a
:class:`~cerebrum.infrastructure.database.models.conversation.Conversation`
— CIS Phase 4 Prompt 2's Message Model. Many rows per conversation
(unlike ``Conversation`` itself), append-only: a message is never
updated or individually deleted after creation — only the owning
conversation's lifecycle (archive/delete) affects it, the same
"append-only child rows, mutable parent lifecycle" shape
cerebrum.infrastructure.database.models.chunk.Chunk's docstring
established for ``DocumentVersion``/``Chunk``.
"""

import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    sequence_index: Mapped[int] = mapped_column(Integer, index=True)
    """0-based order within the conversation — ``created_at`` alone
    isn't a safe ordering key at this resolution (two messages
    persisted within the same clock tick, or a future bulk-import
    path), and
    cerebrum.infrastructure.database.models.conversation.Conversation.summarized_through_sequence
    compares directly against this column.
    """
    role: Mapped[str] = mapped_column(String(20), index=True)
    content: Mapped[str] = mapped_column(Text)
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    """The Citation Support this message's answer carries — each entry
    the same shape
    cerebrum.api.schemas.retrieval.EnrichedCitationResponse serializes,
    persisted as plain JSON (not a foreign-keyed join table) since a
    citation here is a point-in-time record of what was cited, not a
    live reference that should update if the source document changes.
    Empty for ``USER``/``SYSTEM`` messages.
    """
    context_references: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    """Every chunk/entity/document id this message's retrieval actually
    considered (the full retrieval-result reference set — a superset of
    ``citations``, which is only what the model's answer ended up
    citing) — CIS Phase 4 Prompt 2's "Retrieved context references"
    field, and what
    cerebrum.application.conversation.memory_service.MemoryService's
    retrieval-aware memory reads back for follow-up questions.
    """
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    """``None`` for ``USER``/``SYSTEM`` messages — confidence is only
    ever computed for a generated (``ASSISTANT``) answer, see
    cerebrum.application.ai.ai_response_service.AIResponseService.
    """
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
