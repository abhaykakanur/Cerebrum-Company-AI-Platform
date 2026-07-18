"""``AuthenticationService``: login, refresh (with rotation), and
logout — the three use cases behind CIS Phase 1 Prompt 5's Login/Refresh/Logout
endpoints (see cerebrum.api.v1.auth).
"""

import asyncio
from datetime import timedelta

from cerebrum.application.auth.audit_service import AuditService
from cerebrum.application.auth.dtos import TokenPair
from cerebrum.config.security import SecuritySettings
from cerebrum.infrastructure.database.models.audit import AuditEventType
from cerebrum.infrastructure.database.models.session import UserSession
from cerebrum.infrastructure.database.models.user import User
from cerebrum.infrastructure.security.hashing import hash_secret
from cerebrum.infrastructure.security.jwt import TokenService, TokenType
from cerebrum.infrastructure.security.password import PasswordHasher
from cerebrum.repositories.postgres.session_repository import UserSessionRepository
from cerebrum.repositories.postgres.user_repository import UserRepository
from cerebrum.shared.errors.exceptions import (
    AuthenticationException,
    InvalidTokenException,
)
from cerebrum.utils.clock import utcnow

_GENERIC_LOGIN_FAILURE_MESSAGE = "Incorrect email or password."
"""Deliberately identical whether the email doesn't exist or the
password is wrong — distinguishing the two in the response would let a
caller enumerate valid accounts. Both cases are still distinguishable in
the audit trail (see :meth:`AuthenticationService.login`), which is not
caller-visible.
"""


class AuthenticationService:
    def __init__(
        self,
        *,
        user_repository: UserRepository,
        session_repository: UserSessionRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
        audit_service: AuditService,
        settings: SecuritySettings,
    ) -> None:
        self._users = user_repository
        self._sessions = session_repository
        self._password_hasher = password_hasher
        self._tokens = token_service
        self._audit = audit_service
        self._settings = settings

    async def login(
        self,
        *,
        email: str,
        password: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> TokenPair:
        user = await self._users.get_by_email(email)
        if user is None or not user.is_active:
            await self._audit.record(
                AuditEventType.LOGIN_FAILED,
                ip_address=ip_address,
                metadata={"reason": "no_such_active_user"},
            )
            raise AuthenticationException(_GENERIC_LOGIN_FAILURE_MESSAGE)

        # CIS Phase 1 Prompt 7's Performance Review: argon2-cffi's
        # verify()/hash() are CPU-bound, blocking calls (tens to hundreds
        # of milliseconds at this codebase's configured cost parameters —
        # see cerebrum.config.security.SecuritySettings's
        # password_hash_*_cost fields) — calling either synchronously
        # inside this coroutine would stall the entire event loop, and
        # every other request this process is serving, for that whole
        # window. asyncio.to_thread offloads the computation to a worker
        # thread, the same pattern already established for MinIO's
        # synchronous SDK in cerebrum.infrastructure.storage.manager.
        password_matches = await asyncio.to_thread(
            self._password_hasher.verify, password, user.hashed_password
        )
        if not password_matches:
            await self._audit.record(
                AuditEventType.LOGIN_FAILED,
                user_id=user.id,
                organization_id=user.organization_id,
                ip_address=ip_address,
                metadata={"reason": "incorrect_password"},
            )
            raise AuthenticationException(_GENERIC_LOGIN_FAILURE_MESSAGE)

        if self._password_hasher.needs_rehash(user.hashed_password):
            # Migrate to the current hash parameters on a successful
            # login, rather than requiring every user to reset their
            # password after an operator raises the cost factor — see
            # cerebrum.infrastructure.security.password.PasswordHasher.needs_rehash.
            user.hashed_password = await asyncio.to_thread(
                self._password_hasher.hash, password
            )
            await self._users.update(user)

        token_pair = await self._issue_tokens(
            user, ip_address=ip_address, user_agent=user_agent
        )
        await self._audit.record(
            AuditEventType.LOGIN,
            user_id=user.id,
            organization_id=user.organization_id,
            ip_address=ip_address,
        )
        return token_pair

    async def refresh(
        self, *, refresh_token: str, ip_address: str | None, user_agent: str | None
    ) -> TokenPair:
        """Token Rotation: the presented refresh token is revoked and a
        brand-new access/refresh pair is issued, rather than reusing the
        same refresh token across multiple access-token renewals. A
        stolen-and-reused refresh token is detectable (its session row
        is already revoked when the legitimate client's next refresh
        attempt happens), a stolen-and-unused access token still expires
        on its own short schedule.
        """
        payload = self._tokens.decode_token(
            refresh_token, expected_type=TokenType.REFRESH
        )

        session = await self._sessions.get_by_refresh_token_hash(
            hash_secret(refresh_token)
        )
        if session is None or not session.is_active:
            raise InvalidTokenException(
                "Refresh token is not recognized or has been revoked."
            )

        user = await self._users.get_by_id(payload.subject)
        if user is None or not user.is_active:
            raise AuthenticationException("Account is no longer active.")

        session.revoked_at = utcnow()
        await self._sessions.update(session)

        token_pair = await self._issue_tokens(
            user, ip_address=ip_address, user_agent=user_agent
        )
        await self._audit.record(
            AuditEventType.TOKEN_REFRESH,
            user_id=user.id,
            organization_id=user.organization_id,
            ip_address=ip_address,
        )
        return token_pair

    async def logout(self, *, refresh_token: str, ip_address: str | None) -> None:
        """Idempotent: logging out with an already-revoked or unknown
        refresh token succeeds silently rather than raising — the
        caller's goal ("this token must not work anymore") is already
        satisfied.
        """
        session = await self._sessions.get_by_refresh_token_hash(
            hash_secret(refresh_token)
        )
        if session is None or session.revoked_at is not None:
            return

        session.revoked_at = utcnow()
        await self._sessions.update(session)
        await self._audit.record(
            AuditEventType.LOGOUT,
            user_id=session.user_id,
            ip_address=ip_address,
        )

    async def _issue_tokens(
        self, user: User, *, ip_address: str | None, user_agent: str | None
    ) -> TokenPair:
        access_token = self._tokens.create_access_token(
            user_id=user.id, organization_id=user.organization_id
        )
        refresh_token, _jti = self._tokens.create_refresh_token(
            user_id=user.id, organization_id=user.organization_id
        )
        session = UserSession(
            user_id=user.id,
            refresh_token_hash=hash_secret(refresh_token),
            expires_at=utcnow()
            + timedelta(days=self._settings.refresh_token_expire_days),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._sessions.add(session)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self._settings.access_token_expire_minutes * 60,
        )
