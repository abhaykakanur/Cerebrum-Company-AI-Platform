"""``APIKeyService``: generation, validation, rotation, and revocation.
No connector integration yet — see CIS Phase 1 Prompt 5's scope; this is
the foundation a future connector authenticates through.
"""

import secrets
import uuid
from datetime import timedelta

from cerebrum.config.security import SecuritySettings
from cerebrum.infrastructure.database.models.api_key import APIKey
from cerebrum.infrastructure.security.hashing import hash_secret
from cerebrum.repositories.postgres.api_key_repository import APIKeyRepository
from cerebrum.shared.errors.exceptions import (
    AuthenticationException,
    ValidationException,
)
from cerebrum.utils.clock import utcnow

_KEY_PREFIX = "ck_"
"""Every raw key starts with this — a caller (or a secret-scanning
tool) can identify "this looks like a Cerebrum API key" from the string
alone, the same convention GitHub/Stripe/OpenAI tokens use.
"""


class APIKeyService:
    def __init__(
        self, *, api_key_repository: APIKeyRepository, settings: SecuritySettings
    ) -> None:
        self._api_keys = api_key_repository
        self._settings = settings

    async def generate(
        self,
        *,
        user_id: uuid.UUID,
        name: str,
        scopes: list[str],
        expires_in_days: int | None = None,
    ) -> tuple[APIKey, str]:
        """Returns ``(record, raw_key)``. ``raw_key`` is returned exactly
        once — the caller (see cerebrum.api.v1.auth) must surface it to
        the user immediately; it is never recoverable afterward, only
        rotatable (see :meth:`rotate`).
        """
        raw_key = _KEY_PREFIX + secrets.token_urlsafe(32)
        record = APIKey(
            user_id=user_id,
            name=name,
            key_prefix=raw_key[: len(_KEY_PREFIX) + 8],
            hashed_key=hash_secret(raw_key),
            scopes=scopes,
            expires_at=utcnow()
            + timedelta(
                days=expires_in_days or self._settings.api_key_default_expire_days
            ),
        )
        await self._api_keys.add(record)
        return record, raw_key

    async def validate(self, raw_key: str) -> APIKey:
        """Raises :class:`~cerebrum.shared.errors.exceptions.AuthenticationException`
        for a key that doesn't exist, is revoked, or has expired — never
        distinguishing which, for the same no-enumeration reason as
        :class:`~cerebrum.application.auth.authentication_service.AuthenticationService`'s
        login failure message.
        """
        record = await self._api_keys.get_by_hashed_key(hash_secret(raw_key))
        if record is None or not record.is_active:
            raise AuthenticationException("API key is invalid, expired, or revoked.")

        record.last_used_at = utcnow()
        await self._api_keys.update(record)
        return record

    async def revoke(self, api_key_id: uuid.UUID) -> None:
        record = await self._api_keys.get_by_id(api_key_id)
        if record is None:
            raise ValidationException(f"No API key with id {api_key_id}.")
        record.revoked_at = utcnow()
        await self._api_keys.update(record)

    async def rotate(self, api_key_id: uuid.UUID) -> tuple[APIKey, str]:
        """Revokes ``api_key_id`` and generates a replacement with the
        same name/scopes — the caller gets a new raw key; the old one
        stops working immediately.
        """
        old_record = await self._api_keys.get_by_id(api_key_id)
        if old_record is None:
            raise ValidationException(f"No API key with id {api_key_id}.")

        await self.revoke(api_key_id)
        return await self.generate(
            user_id=old_record.user_id, name=old_record.name, scopes=old_record.scopes
        )
