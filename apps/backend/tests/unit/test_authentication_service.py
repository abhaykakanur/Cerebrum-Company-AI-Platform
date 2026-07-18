"""Proves the acceptance criteria "Users can authenticate" and "Refresh
flow works" from CIS Phase 1 Prompt 5, against an in-memory SQLite
database (see apps/backend/tests/conftest.py's ``db_session`` fixture).
"""

import asyncio

import pytest
from _auth_factories import seed_tenant_with_user
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.auth.audit_service import AuditService
from cerebrum.application.auth.authentication_service import AuthenticationService
from cerebrum.config.security import SecuritySettings
from cerebrum.infrastructure.security.jwt import TokenService, TokenType
from cerebrum.infrastructure.security.password import PasswordHasher
from cerebrum.repositories.postgres.audit_repository import AuditEventRepository
from cerebrum.repositories.postgres.session_repository import UserSessionRepository
from cerebrum.repositories.postgres.user_repository import UserRepository
from cerebrum.shared.errors.exceptions import (
    AuthenticationException,
    InvalidTokenException,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def security_settings() -> SecuritySettings:
    return SecuritySettings()


@pytest.fixture
def hasher(security_settings: SecuritySettings) -> PasswordHasher:
    return PasswordHasher(security_settings)


@pytest.fixture
def token_service(security_settings: SecuritySettings) -> TokenService:
    return TokenService(security_settings)


def _build_service(
    session: AsyncSession,
    hasher: PasswordHasher,
    token_service: TokenService,
    security_settings: SecuritySettings,
) -> AuthenticationService:
    return AuthenticationService(
        user_repository=UserRepository(session),
        session_repository=UserSessionRepository(session),
        password_hasher=hasher,
        token_service=token_service,
        audit_service=AuditService(AuditEventRepository(session)),
        settings=security_settings,
    )


async def test_login_with_correct_credentials_returns_a_token_pair(
    db_session: AsyncSession,
    hasher: PasswordHasher,
    token_service: TokenService,
    security_settings: SecuritySettings,
) -> None:
    tenant = await seed_tenant_with_user(db_session, hasher)
    service = _build_service(db_session, hasher, token_service, security_settings)

    pair = await service.login(
        email=tenant.user_email,
        password=tenant.user_password,
        ip_address="127.0.0.1",
        user_agent="pytest",
    )
    await db_session.commit()

    assert pair.access_token
    assert pair.refresh_token
    assert pair.token_type == "bearer"
    assert pair.expires_in == security_settings.access_token_expire_minutes * 60

    payload = token_service.decode_token(
        pair.access_token, expected_type=TokenType.ACCESS
    )
    assert payload.subject == tenant.user_id
    assert payload.organization_id == tenant.organization_id


async def test_login_with_wrong_password_is_rejected(
    db_session: AsyncSession,
    hasher: PasswordHasher,
    token_service: TokenService,
    security_settings: SecuritySettings,
) -> None:
    tenant = await seed_tenant_with_user(db_session, hasher)
    service = _build_service(db_session, hasher, token_service, security_settings)

    with pytest.raises(AuthenticationException):
        await service.login(
            email=tenant.user_email,
            password="wrong",
            ip_address="1.2.3.4",
            user_agent="pytest",
        )


async def test_login_with_unknown_email_matches_wrong_password_error_message(
    db_session: AsyncSession,
    hasher: PasswordHasher,
    token_service: TokenService,
    security_settings: SecuritySettings,
) -> None:
    """No user enumeration: both failure modes must be indistinguishable
    to the caller — see
    cerebrum.application.auth.authentication_service's
    ``_GENERIC_LOGIN_FAILURE_MESSAGE``.
    """
    tenant = await seed_tenant_with_user(db_session, hasher)
    service = _build_service(db_session, hasher, token_service, security_settings)

    with pytest.raises(AuthenticationException) as unknown_email_exc:
        await service.login(
            email="nobody@example.com",
            password="whatever123!",
            ip_address="1.2.3.4",
            user_agent="pytest",
        )
    with pytest.raises(AuthenticationException) as wrong_password_exc:
        await service.login(
            email=tenant.user_email,
            password="wrong",
            ip_address="1.2.3.4",
            user_agent="pytest",
        )

    assert unknown_email_exc.value.message == wrong_password_exc.value.message


async def test_login_for_inactive_user_is_rejected(
    db_session: AsyncSession,
    hasher: PasswordHasher,
    token_service: TokenService,
    security_settings: SecuritySettings,
) -> None:
    from _auth_factories import create_organization, create_user

    org = await create_organization(db_session)
    await create_user(
        db_session,
        organization_id=org.id,
        email="inactive@example.com",
        password="CorrectHorse123!",
        hasher=hasher,
        is_active=False,
    )
    await db_session.commit()
    service = _build_service(db_session, hasher, token_service, security_settings)

    with pytest.raises(AuthenticationException):
        await service.login(
            email="inactive@example.com",
            password="CorrectHorse123!",
            ip_address="1.2.3.4",
            user_agent="pytest",
        )


async def test_refresh_rotates_the_token_and_issues_a_new_pair(
    db_session: AsyncSession,
    hasher: PasswordHasher,
    token_service: TokenService,
    security_settings: SecuritySettings,
) -> None:
    tenant = await seed_tenant_with_user(db_session, hasher)
    service = _build_service(db_session, hasher, token_service, security_settings)
    original = await service.login(
        email=tenant.user_email,
        password=tenant.user_password,
        ip_address="127.0.0.1",
        user_agent="pytest",
    )
    await db_session.commit()

    refreshed = await service.refresh(
        refresh_token=original.refresh_token,
        ip_address="127.0.0.1",
        user_agent="pytest",
    )
    await db_session.commit()

    assert refreshed.access_token != original.access_token
    assert refreshed.refresh_token != original.refresh_token


async def test_refresh_with_an_already_rotated_token_is_rejected(
    db_session: AsyncSession,
    hasher: PasswordHasher,
    token_service: TokenService,
    security_settings: SecuritySettings,
) -> None:
    """Token Rotation's security property: a refresh token is single-use
    — presenting it again after it has already been exchanged is
    treated as a replay attempt, not honored.
    """
    tenant = await seed_tenant_with_user(db_session, hasher)
    service = _build_service(db_session, hasher, token_service, security_settings)
    original = await service.login(
        email=tenant.user_email,
        password=tenant.user_password,
        ip_address="127.0.0.1",
        user_agent="pytest",
    )
    await db_session.commit()
    await service.refresh(
        refresh_token=original.refresh_token,
        ip_address="127.0.0.1",
        user_agent="pytest",
    )
    await db_session.commit()

    with pytest.raises(InvalidTokenException):
        await service.refresh(
            refresh_token=original.refresh_token,
            ip_address="9.9.9.9",
            user_agent="pytest",
        )


async def test_refresh_with_an_access_token_is_rejected(
    db_session: AsyncSession,
    hasher: PasswordHasher,
    token_service: TokenService,
    security_settings: SecuritySettings,
) -> None:
    tenant = await seed_tenant_with_user(db_session, hasher)
    service = _build_service(db_session, hasher, token_service, security_settings)
    pair = await service.login(
        email=tenant.user_email,
        password=tenant.user_password,
        ip_address="127.0.0.1",
        user_agent="pytest",
    )
    await db_session.commit()

    with pytest.raises(InvalidTokenException):
        await service.refresh(
            refresh_token=pair.access_token, ip_address="127.0.0.1", user_agent="pytest"
        )


async def test_logout_revokes_the_session(
    db_session: AsyncSession,
    hasher: PasswordHasher,
    token_service: TokenService,
    security_settings: SecuritySettings,
) -> None:
    tenant = await seed_tenant_with_user(db_session, hasher)
    service = _build_service(db_session, hasher, token_service, security_settings)
    pair = await service.login(
        email=tenant.user_email,
        password=tenant.user_password,
        ip_address="127.0.0.1",
        user_agent="pytest",
    )
    await db_session.commit()

    await service.logout(refresh_token=pair.refresh_token, ip_address="127.0.0.1")
    await db_session.commit()

    with pytest.raises(InvalidTokenException):
        await service.refresh(
            refresh_token=pair.refresh_token,
            ip_address="127.0.0.1",
            user_agent="pytest",
        )


async def test_logout_is_idempotent(
    db_session: AsyncSession,
    hasher: PasswordHasher,
    token_service: TokenService,
    security_settings: SecuritySettings,
) -> None:
    tenant = await seed_tenant_with_user(db_session, hasher)
    service = _build_service(db_session, hasher, token_service, security_settings)
    pair = await service.login(
        email=tenant.user_email,
        password=tenant.user_password,
        ip_address="127.0.0.1",
        user_agent="pytest",
    )
    await db_session.commit()

    await service.logout(refresh_token=pair.refresh_token, ip_address="127.0.0.1")
    await db_session.commit()
    await service.logout(
        refresh_token=pair.refresh_token, ip_address="127.0.0.1"
    )  # must not raise


async def test_login_does_not_block_the_event_loop(
    db_session: AsyncSession,
    hasher: PasswordHasher,
    token_service: TokenService,
    security_settings: SecuritySettings,
) -> None:
    """CIS Phase 1 Prompt 7's Performance Review: Argon2 verification is
    CPU-bound and must run via ``asyncio.to_thread`` (see
    cerebrum.application.auth.authentication_service.AuthenticationService.login),
    not synchronously on the event loop — a regression here would mean
    every concurrent request this process is serving stalls for the
    duration of one login's password check. Proven by running a trivial
    "ticker" coroutine concurrently with ``login()`` and asserting it
    kept making progress throughout — a blocked event loop would starve
    it entirely until ``login()`` returned.
    """
    tenant = await seed_tenant_with_user(db_session, hasher)
    service = _build_service(db_session, hasher, token_service, security_settings)

    tick_count = 0
    stop = False

    async def _ticker() -> None:
        nonlocal tick_count
        while not stop:
            tick_count += 1
            await asyncio.sleep(0)

    ticker_task = asyncio.create_task(_ticker())
    await service.login(
        email=tenant.user_email,
        password=tenant.user_password,
        ip_address="127.0.0.1",
        user_agent="pytest",
    )
    stop = True
    await ticker_task

    assert tick_count > 5
