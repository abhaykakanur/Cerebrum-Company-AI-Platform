"""``Conversation``: a persistent, workspace-scoped AI conversation —
CIS Phase 4 Prompt 2's Conversation Management. Holds no message
content itself — see
cerebrum.infrastructure.database.models.message.Message for that (a
one-to-many, mirroring
cerebrum.infrastructure.database.models.document.Document /
cerebrum.infrastructure.database.models.document_version.DocumentVersion's
"one row of identity/lifecycle, many rows of the actual content" split).
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    AuditFieldsMixin,
    OptimisticLockMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UTCDateTime,
    UUIDPrimaryKeyMixin,
)


class ConversationStatus(StrEnum):
    """CIS Phase 4 Prompt 2's Conversation Lifecycle: Active -> Archived
    -> Deleted. ``DELETED`` is set alongside (not instead of)
    :class:`~cerebrum.infrastructure.database.models.mixins.SoftDeleteMixin`'s
    ``is_deleted``/``deleted_at`` — the same split
    cerebrum.infrastructure.database.models.document.DocumentStatus's
    docstring already established for ``Document``.
    """

    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class Conversation(
    Base,
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    SoftDeleteMixin,
    AuditFieldsMixin,
    OptimisticLockMixin,
):
    __tablename__ = "conversations"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    """Denormalized off ``workspace_id`` — the same "Tenant" field
    cerebrum.infrastructure.database.models.entity.Entity's docstring
    already established the precedent for.
    """
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    """The owning user — CIS Phase 4 Prompt 2's User Ownership
    requirement; see cerebrum.application.conversation.conversation_service
    for the ownership check every mutating operation enforces.
    """
    session_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    """An opaque, client-supplied correlation id (e.g. a browser tab or
    websocket connection identifier) grouping conversations from the
    same client session — distinct from, and not a foreign key into,
    cerebrum.infrastructure.database.models.session.UserSession (that
    is the authentication/refresh-token session; this is a
    conversational one, per CIS Phase 4 Prompt 2's Session Management,
    which may span, outlive, or be narrower than any single auth
    session).
    """
    title: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(
        String(20), default=ConversationStatus.ACTIVE.value, index=True
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    """The rolling summary CIS Phase 4 Prompt 2's Automatic Conversation
    Summarization produces once the conversation grows past
    cerebrum.application.conversation.conversation_summary_service's
    threshold — covers every message up to (not including)
    ``summarized_through_sequence``; ``None`` until the first
    summarization run.
    """
    summarized_through_sequence: Mapped[int] = mapped_column(Integer, default=-1)
    """The
    :attr:`~cerebrum.infrastructure.database.models.message.Message.sequence_index`
    of the last message already folded into ``summary`` — Context
    Pruning's bookkeeping:
    cerebrum.application.conversation.memory_service.MemoryService reads
    this to build a rolling window from only the messages *after* it
    (``sequence_index > summarized_through_sequence``) rather than the
    full history. ``-1`` (never a real ``sequence_index``, which starts
    at ``0``) is the "nothing summarized yet" sentinel — a plain ``0``
    default would wrongly exclude the very first message from every
    conversation's initial rolling window.
    """
    conversation_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    last_message_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
