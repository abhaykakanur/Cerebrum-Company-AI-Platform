"""Proves the acceptance criterion "API keys validate" from CIS Phase 1
Prompt 5, plus rotation and revocation.
"""

import pytest
from _auth_factories import create_organization, create_user
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.auth.api_key_service import APIKeyService
from cerebrum.config.security import SecuritySettings
from cerebrum.infrastructure.security.password import PasswordHasher
from cerebrum.repositories.postgres.api_key_repository import APIKeyRepository
from cerebrum.shared.errors.exceptions import (
    AuthenticationException,
    ValidationException,
)
from cerebrum.utils.clock import utcnow

pytestmark = pytest.mark.unit


@pytest.fixture
def security_settings() -> SecuritySettings:
    return SecuritySettings()


@pytest.fixture
def hasher(security_settings: SecuritySettings) -> PasswordHasher:
    return PasswordHasher(security_settings)


def _build_service(
    session: AsyncSession, security_settings: SecuritySettings
) -> APIKeyService:
    return APIKeyService(
        api_key_repository=APIKeyRepository(session), settings=security_settings
    )


async def _seed_user(db_session: AsyncSession, hasher: PasswordHasher):
    org = await create_organization(db_session)
    user = await create_user(
        db_session,
        organization_id=org.id,
        email="dev@example.com",
        password="CorrectHorse123!",
        hasher=hasher,
    )
    await db_session.commit()
    return user


async def test_generated_key_starts_with_the_cerebrum_prefix(
    db_session: AsyncSession,
    hasher: PasswordHasher,
    security_settings: SecuritySettings,
) -> None:
    user = await _seed_user(db_session, hasher)
    service = _build_service(db_session, security_settings)

    record, raw_key = await service.generate(
        user_id=user.id, name="ci", scopes=["read"]
    )
    await db_session.commit()

    assert raw_key.startswith("ck_")
    assert record.key_prefix == raw_key[: len(record.key_prefix)]


async def test_raw_key_is_never_stored(
    db_session: AsyncSession,
    hasher: PasswordHasher,
    security_settings: SecuritySettings,
) -> None:
    user = await _seed_user(db_session, hasher)
    service = _build_service(db_session, security_settings)

    record, raw_key = await service.generate(
        user_id=user.id, name="ci", scopes=["read"]
    )
    await db_session.commit()

    assert record.hashed_key != raw_key
    assert raw_key not in record.hashed_key


async def test_validate_accepts_a_freshly_generated_key(
    db_session: AsyncSession,
    hasher: PasswordHasher,
    security_settings: SecuritySettings,
) -> None:
    user = await _seed_user(db_session, hasher)
    service = _build_service(db_session, security_settings)
    record, raw_key = await service.generate(
        user_id=user.id, name="ci", scopes=["read"]
    )
    await db_session.commit()

    validated = await service.validate(raw_key)
    await db_session.commit()

    assert validated.id == record.id
    assert validated.last_used_at is not None


async def test_validate_rejects_an_unknown_key(
    db_session: AsyncSession, security_settings: SecuritySettings
) -> None:
    service = _build_service(db_session, security_settings)
    with pytest.raises(AuthenticationException):
        await service.validate("ck_this-key-does-not-exist")


async def test_validate_rejects_a_revoked_key(
    db_session: AsyncSession,
    hasher: PasswordHasher,
    security_settings: SecuritySettings,
) -> None:
    user = await _seed_user(db_session, hasher)
    service = _build_service(db_session, security_settings)
    record, raw_key = await service.generate(
        user_id=user.id, name="ci", scopes=["read"]
    )
    await db_session.commit()

    await service.revoke(record.id)
    await db_session.commit()

    with pytest.raises(AuthenticationException):
        await service.validate(raw_key)


async def test_validate_rejects_an_expired_key(
    db_session: AsyncSession,
    hasher: PasswordHasher,
    security_settings: SecuritySettings,
) -> None:
    user = await _seed_user(db_session, hasher)
    service = _build_service(db_session, security_settings)
    record, raw_key = await service.generate(
        user_id=user.id, name="ci", scopes=["read"], expires_in_days=1
    )
    record.expires_at = utcnow()  # force it into the past
    await db_session.commit()

    with pytest.raises(AuthenticationException):
        await service.validate(raw_key)


async def test_rotate_invalidates_the_old_key_and_issues_a_new_one(
    db_session: AsyncSession,
    hasher: PasswordHasher,
    security_settings: SecuritySettings,
) -> None:
    user = await _seed_user(db_session, hasher)
    service = _build_service(db_session, security_settings)
    old_record, old_raw_key = await service.generate(
        user_id=user.id, name="ci", scopes=["read"]
    )
    await db_session.commit()

    new_record, new_raw_key = await service.rotate(old_record.id)
    await db_session.commit()

    assert new_raw_key != old_raw_key
    assert new_record.name == old_record.name
    assert new_record.scopes == old_record.scopes
    with pytest.raises(AuthenticationException):
        await service.validate(old_raw_key)
    validated = await service.validate(new_raw_key)
    await db_session.commit()
    assert validated.id == new_record.id


async def test_revoke_of_unknown_key_raises(
    db_session: AsyncSession, security_settings: SecuritySettings
) -> None:
    import uuid

    service = _build_service(db_session, security_settings)
    with pytest.raises(ValidationException):
        await service.revoke(uuid.uuid4())
