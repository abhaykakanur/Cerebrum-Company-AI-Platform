"""``APIKey``: a long-lived, non-interactive credential — see
docs/architecture/security/api-key-guide.md. No connector integration
yet (CIS Phase 1 Prompt 5's scope) — this is the storage/validation
foundation a future connector authenticates through.
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    TimestampMixin,
    UTCDateTime,
    UUIDPrimaryKeyMixin,
)
from cerebrum.utils.clock import ensure_utc, utcnow


class APIKey(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Only ``hashed_key`` is stored — the raw key is returned to the
    caller exactly once, at creation, and never persisted or logged; see
    cerebrum.application.auth.api_key_service. ``key_prefix`` (a short,
    non-secret slice of the raw key) is stored in cleartext so a user
    can identify which key is which in a list view without the full
    secret ever being displayed again.
    """

    __tablename__ = "api_keys"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    key_prefix: Mapped[str] = mapped_column(String(12), index=True)
    hashed_key: Mapped[str] = mapped_column(String(255), unique=True)
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    @property
    def is_active(self) -> bool:
        """Neither revoked nor past its expiry — mirrors
        :attr:`~cerebrum.infrastructure.database.models.session.UserSession.is_active`.
        """
        if self.revoked_at is not None:
            return False
        return self.expires_at is None or ensure_utc(self.expires_at) > utcnow()
