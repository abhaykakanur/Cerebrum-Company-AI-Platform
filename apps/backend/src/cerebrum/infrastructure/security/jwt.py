"""JWT issuance and validation — access tokens, refresh tokens, and
token rotation. Wraps PyJWT — never imported directly outside this
module, per cerebrum.infrastructure.security's package docstring.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

import jwt

from cerebrum.config.security import SecuritySettings
from cerebrum.shared.errors.exceptions import (
    ExpiredTokenException,
    InvalidTokenException,
)
from cerebrum.utils.clock import utcnow


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


@dataclass(frozen=True, slots=True)
class TokenPayload:
    """A decoded, validated token's claims — never constructed directly
    from untrusted input; only :meth:`TokenService.decode_token` builds
    one, after signature and expiry have already passed.
    """

    subject: uuid.UUID
    """The authenticated user's ID (JWT ``sub`` claim)."""

    organization_id: uuid.UUID
    """The user's tenant (JWT ``org_id`` claim) — see
    docs/architecture/security/multi-tenancy-guide.md.
    """

    token_type: TokenType
    jti: uuid.UUID
    """Unique per issued token — a refresh token's ``jti`` is what
    :class:`~cerebrum.infrastructure.database.models.session.UserSession`
    tracking correlates against (see
    cerebrum.application.auth.authentication_service), enabling
    revocation of one specific token without invalidating every session.
    """

    issued_at: datetime
    expires_at: datetime


class TokenService:
    """Issues and validates access/refresh tokens signed with
    ``SecuritySettings.jwt_secret_key`` using ``SecuritySettings.jwt_algorithm``
    (HMAC by default — a single shared secret signs and verifies; no
    asymmetric keypair is provisioned at this milestone).
    """

    def __init__(self, settings: SecuritySettings) -> None:
        self._settings = settings

    def create_access_token(
        self, *, user_id: uuid.UUID, organization_id: uuid.UUID
    ) -> str:
        return self._encode(
            user_id=user_id,
            organization_id=organization_id,
            token_type=TokenType.ACCESS,
            lifetime=timedelta(minutes=self._settings.access_token_expire_minutes),
            jti=uuid.uuid4(),
        )

    def create_refresh_token(
        self,
        *,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        jti: uuid.UUID | None = None,
    ) -> tuple[str, uuid.UUID]:
        """Returns ``(token, jti)``. ``jti`` may be supplied by the
        caller (see
        cerebrum.application.auth.authentication_service's rotation
        flow, which reuses a specific ``jti`` when re-issuing) or left
        ``None`` to generate a fresh one — the common case, at login.
        """
        token_id = jti or uuid.uuid4()
        token = self._encode(
            user_id=user_id,
            organization_id=organization_id,
            token_type=TokenType.REFRESH,
            lifetime=timedelta(days=self._settings.refresh_token_expire_days),
            jti=token_id,
        )
        return token, token_id

    def decode_token(self, token: str, *, expected_type: TokenType) -> TokenPayload:
        """Raises :class:`~cerebrum.shared.errors.exceptions.ExpiredTokenException`
        for a lapsed ``exp`` claim, or
        :class:`~cerebrum.shared.errors.exceptions.InvalidTokenException`
        for every other validation failure (bad signature, malformed
        token, wrong ``token_type`` — e.g. a refresh token presented
        where an access token is required) — never PyJWT's own
        exception types, per CIS Phase 1 Prompt 4's "never leak driver
        exceptions" rule, extended here to every third-party library
        this layer wraps.
        """
        try:
            claims = jwt.decode(
                token,
                self._settings.jwt_secret_key.get_secret_value(),
                algorithms=[self._settings.jwt_algorithm],
            )
        except jwt.ExpiredSignatureError as exc:
            raise ExpiredTokenException(cause=exc) from exc
        except jwt.PyJWTError as exc:
            raise InvalidTokenException(cause=exc) from exc

        try:
            payload = TokenPayload(
                subject=uuid.UUID(claims["sub"]),
                organization_id=uuid.UUID(claims["org_id"]),
                token_type=TokenType(claims["type"]),
                jti=uuid.UUID(claims["jti"]),
                issued_at=datetime.fromtimestamp(claims["iat"], tz=utcnow().tzinfo),
                expires_at=datetime.fromtimestamp(claims["exp"], tz=utcnow().tzinfo),
            )
        except (KeyError, ValueError) as exc:
            raise InvalidTokenException(
                "Token is missing or has malformed required claims.", cause=exc
            ) from exc

        if payload.token_type is not expected_type:
            raise InvalidTokenException(
                f"Expected a {expected_type.value} token, "
                f"got {payload.token_type.value}."
            )
        return payload

    def _encode(
        self,
        *,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        token_type: TokenType,
        lifetime: timedelta,
        jti: uuid.UUID,
    ) -> str:
        now = utcnow()
        claims = {
            "sub": str(user_id),
            "org_id": str(organization_id),
            "type": token_type.value,
            "jti": str(jti),
            "iat": now,
            "exp": now + lifetime,
        }
        return jwt.encode(
            claims,
            self._settings.jwt_secret_key.get_secret_value(),
            algorithm=self._settings.jwt_algorithm,
        )
