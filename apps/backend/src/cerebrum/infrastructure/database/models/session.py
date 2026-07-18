"""``UserSession``: refresh-token tracking, one row per issued refresh
token. Named ``UserSession`` — not ``Session`` — to avoid colliding with
``sqlalchemy.orm.Session``/``AsyncSession`` (see
cerebrum.infrastructure.database.session) or Python's own vocabulary for
an ORM unit of work; this is a *login* session, a distinct concept.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    TimestampMixin,
    UTCDateTime,
    UUIDPrimaryKeyMixin,
)
from cerebrum.utils.clock import ensure_utc, utcnow


class UserSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Only ``refresh_token_hash`` is stored — the raw refresh token is
    never persisted, matching
    :class:`~cerebrum.infrastructure.database.models.api_key.APIKey`'s
    hashed-secret pattern. ``device_metadata`` is a placeholder JSON blob
    (CIS Phase 1 Prompt 5 asks for "Device metadata placeholder"
    specifically, not a parsed User-Agent/device-fingerprinting
    implementation).
    """

    __tablename__ = "user_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    refresh_token_hash: Mapped[str] = mapped_column(
        String(255), unique=True, index=True
    )
    device_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_used_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    @property
    def is_active(self) -> bool:
        """Neither revoked nor past its expiry — the single check every
        refresh-flow and session-listing call site should use instead of
        re-deriving this in multiple places.
        """
        return self.revoked_at is None and ensure_utc(self.expires_at) > utcnow()
