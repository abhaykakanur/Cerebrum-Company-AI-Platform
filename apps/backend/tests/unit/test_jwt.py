"""Proves the acceptance criterion "JWT validation works" from CIS Phase
1 Prompt 5, including Token Expiration and Token Rotation-adjacent
behavior (distinct ``jti`` per issuance).
"""

import uuid
from datetime import timedelta

import pytest

from cerebrum.config.security import SecuritySettings
from cerebrum.infrastructure.security.jwt import TokenService, TokenType
from cerebrum.shared.errors.exceptions import (
    ExpiredTokenException,
    InvalidTokenException,
)
from cerebrum.utils.clock import utcnow

pytestmark = pytest.mark.unit


@pytest.fixture
def token_service() -> TokenService:
    return TokenService(SecuritySettings())


def test_access_token_round_trips(token_service: TokenService) -> None:
    user_id, org_id = uuid.uuid4(), uuid.uuid4()
    token = token_service.create_access_token(user_id=user_id, organization_id=org_id)

    payload = token_service.decode_token(token, expected_type=TokenType.ACCESS)

    assert payload.subject == user_id
    assert payload.organization_id == org_id
    assert payload.token_type is TokenType.ACCESS


def test_refresh_token_round_trips_and_returns_its_jti(
    token_service: TokenService,
) -> None:
    user_id, org_id = uuid.uuid4(), uuid.uuid4()
    token, jti = token_service.create_refresh_token(
        user_id=user_id, organization_id=org_id
    )

    payload = token_service.decode_token(token, expected_type=TokenType.REFRESH)

    assert payload.jti == jti
    assert payload.token_type is TokenType.REFRESH


def test_two_tokens_for_the_same_user_have_different_jti(
    token_service: TokenService,
) -> None:
    user_id, org_id = uuid.uuid4(), uuid.uuid4()
    _, first_jti = token_service.create_refresh_token(
        user_id=user_id, organization_id=org_id
    )
    _, second_jti = token_service.create_refresh_token(
        user_id=user_id, organization_id=org_id
    )
    assert first_jti != second_jti


def test_presenting_a_refresh_token_where_access_is_expected_is_rejected(
    token_service: TokenService,
) -> None:
    refresh_token, _ = token_service.create_refresh_token(
        user_id=uuid.uuid4(), organization_id=uuid.uuid4()
    )
    with pytest.raises(InvalidTokenException):
        token_service.decode_token(refresh_token, expected_type=TokenType.ACCESS)


def test_tampered_signature_is_rejected(token_service: TokenService) -> None:
    token = token_service.create_access_token(
        user_id=uuid.uuid4(), organization_id=uuid.uuid4()
    )
    tampered = token[:-4] + ("A" if token[-4] != "A" else "B") + token[-3:]
    with pytest.raises(InvalidTokenException):
        token_service.decode_token(tampered, expected_type=TokenType.ACCESS)


def test_malformed_token_is_rejected(token_service: TokenService) -> None:
    with pytest.raises(InvalidTokenException):
        token_service.decode_token("not-a-jwt-at-all", expected_type=TokenType.ACCESS)


def test_token_signed_with_a_different_secret_is_rejected() -> None:
    issuer = TokenService(SecuritySettings(jwt_secret_key="secret-one"))  # type: ignore[arg-type]
    verifier = TokenService(SecuritySettings(jwt_secret_key="secret-two"))  # type: ignore[arg-type]
    token = issuer.create_access_token(
        user_id=uuid.uuid4(), organization_id=uuid.uuid4()
    )
    with pytest.raises(InvalidTokenException):
        verifier.decode_token(token, expected_type=TokenType.ACCESS)


def _encode_expired_access_token(settings: SecuritySettings) -> str:
    """Crafts a token identical in shape to
    :meth:`TokenService.create_access_token`'s output but with an
    already-past ``exp`` — ``access_token_expire_minutes`` itself is
    constrained to be positive (``gt=0``), so an already-expired token
    can't be produced through the service's normal issuance path.
    """
    import jwt as pyjwt

    now = utcnow()
    claims = {
        "sub": str(uuid.uuid4()),
        "org_id": str(uuid.uuid4()),
        "type": TokenType.ACCESS.value,
        "jti": str(uuid.uuid4()),
        "iat": now - timedelta(minutes=10),
        "exp": now - timedelta(minutes=5),
    }
    return pyjwt.encode(
        claims,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def test_expired_access_token_is_rejected_with_the_specific_exception() -> None:
    settings = SecuritySettings()
    token = _encode_expired_access_token(settings)

    with pytest.raises(ExpiredTokenException):
        TokenService(settings).decode_token(token, expected_type=TokenType.ACCESS)


def test_expired_token_is_not_confused_with_an_invalid_one() -> None:
    """``ExpiredTokenException`` and ``InvalidTokenException`` are
    siblings — both direct subclasses of ``AuthenticationException`` —
    not one a subclass of the other, so catching one never accidentally
    catches the other.
    """
    settings = SecuritySettings()
    token = _encode_expired_access_token(settings)

    try:
        TokenService(settings).decode_token(token, expected_type=TokenType.ACCESS)
    except ExpiredTokenException:
        pass
    except InvalidTokenException:
        pytest.fail(
            "An expired token must raise ExpiredTokenException, not the base type."
        )


def test_access_and_refresh_lifetimes_are_configurable() -> None:
    before = utcnow()
    settings = SecuritySettings(
        access_token_expire_minutes=5, refresh_token_expire_days=2
    )
    service = TokenService(settings)

    access = service.create_access_token(
        user_id=uuid.uuid4(), organization_id=uuid.uuid4()
    )
    access_payload = service.decode_token(access, expected_type=TokenType.ACCESS)
    assert access_payload.expires_at - before <= timedelta(minutes=5, seconds=5)

    refresh, _ = service.create_refresh_token(
        user_id=uuid.uuid4(), organization_id=uuid.uuid4()
    )
    refresh_payload = service.decode_token(refresh, expected_type=TokenType.REFRESH)
    assert refresh_payload.expires_at - before <= timedelta(days=2, seconds=5)
