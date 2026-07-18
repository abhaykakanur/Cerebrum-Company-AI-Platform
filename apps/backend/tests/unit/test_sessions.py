"""Proves the acceptance criterion "Sessions are tracked" from CIS Phase
1 Prompt 5 — direct coverage of
:class:`~cerebrum.infrastructure.database.models.session.UserSession`
and
:class:`~cerebrum.repositories.postgres.session_repository.UserSessionRepository`,
beyond what test_authentication_service.py already exercises through
the login/refresh/logout flow.
"""

import uuid
from datetime import timedelta

import pytest
from _auth_factories import create_organization, create_user
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.config.security import SecuritySettings
from cerebrum.infrastructure.database.models.session import UserSession
from cerebrum.infrastructure.security.hashing import hash_secret
from cerebrum.infrastructure.security.password import PasswordHasher
from cerebrum.repositories.postgres.session_repository import UserSessionRepository
from cerebrum.utils.clock import utcnow

pytestmark = pytest.mark.unit


@pytest.fixture
def hasher() -> PasswordHasher:
    return PasswordHasher(SecuritySettings())


async def _seed_user(db_session: AsyncSession, hasher: PasswordHasher):
    org = await create_organization(db_session)
    user = await create_user(
        db_session,
        organization_id=org.id,
        email="carol@example.com",
        password="CorrectHorse123!",
        hasher=hasher,
    )
    await db_session.commit()
    return user


def test_is_active_is_true_for_a_fresh_unrevoked_session() -> None:
    session_row = UserSession(
        user_id=uuid.uuid4(),
        refresh_token_hash=hash_secret("token"),
        expires_at=utcnow() + timedelta(days=1),
    )
    assert session_row.is_active is True


def test_is_active_is_false_once_revoked() -> None:
    session_row = UserSession(
        user_id=uuid.uuid4(),
        refresh_token_hash=hash_secret("token"),
        expires_at=utcnow() + timedelta(days=1),
        revoked_at=utcnow(),
    )
    assert session_row.is_active is False


def test_is_active_is_false_once_expired() -> None:
    session_row = UserSession(
        user_id=uuid.uuid4(),
        refresh_token_hash=hash_secret("token"),
        expires_at=utcnow() - timedelta(seconds=1),
    )
    assert session_row.is_active is False


async def test_get_by_refresh_token_hash_finds_the_matching_session(
    db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    user = await _seed_user(db_session, hasher)
    repository = UserSessionRepository(db_session)
    session_row = UserSession(
        user_id=user.id,
        refresh_token_hash=hash_secret("a-refresh-token"),
        expires_at=utcnow() + timedelta(days=1),
        ip_address="127.0.0.1",
        user_agent="pytest",
    )
    await repository.add(session_row)
    await db_session.commit()

    found = await repository.get_by_refresh_token_hash(hash_secret("a-refresh-token"))
    assert found is not None
    assert found.id == session_row.id


async def test_list_active_for_user_excludes_revoked_and_expired_sessions(
    db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    user = await _seed_user(db_session, hasher)
    repository = UserSessionRepository(db_session)

    active = UserSession(
        user_id=user.id,
        refresh_token_hash=hash_secret("active-token"),
        expires_at=utcnow() + timedelta(days=1),
    )
    revoked = UserSession(
        user_id=user.id,
        refresh_token_hash=hash_secret("revoked-token"),
        expires_at=utcnow() + timedelta(days=1),
        revoked_at=utcnow(),
    )
    expired = UserSession(
        user_id=user.id,
        refresh_token_hash=hash_secret("expired-token"),
        expires_at=utcnow() - timedelta(seconds=1),
    )
    for session_row in (active, revoked, expired):
        await repository.add(session_row)
    await db_session.commit()

    active_sessions = await repository.list_active_for_user(user.id)

    assert [s.id for s in active_sessions] == [active.id]


async def test_device_metadata_defaults_to_an_empty_placeholder(
    db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    """CIS Phase 1 Prompt 5 asks for a "Device metadata placeholder" —
    not a parsed device-fingerprinting implementation. Confirms the
    column round-trips a plain dict without requiring one to be set.
    """
    user = await _seed_user(db_session, hasher)
    repository = UserSessionRepository(db_session)
    session_row = UserSession(
        user_id=user.id,
        refresh_token_hash=hash_secret("token"),
        expires_at=utcnow() + timedelta(days=1),
    )
    await repository.add(session_row)
    await db_session.commit()

    reloaded = await repository.get_by_id(session_row.id)
    assert reloaded is not None
    assert reloaded.device_metadata == {}
