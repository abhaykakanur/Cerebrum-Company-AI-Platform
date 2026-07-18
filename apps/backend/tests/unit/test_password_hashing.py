"""Proves the acceptance criterion "Passwords are securely hashed" from
CIS Phase 1 Prompt 5.
"""

import pytest

from cerebrum.config.security import SecuritySettings
from cerebrum.infrastructure.security.password import (
    PasswordHasher,
    validate_password_policy,
)
from cerebrum.shared.errors.exceptions import ValidationException

pytestmark = pytest.mark.unit

_VALID_PASSWORD = "CorrectHorse123!"


@pytest.fixture
def security_settings() -> SecuritySettings:
    return SecuritySettings()


@pytest.fixture
def hasher(security_settings: SecuritySettings) -> PasswordHasher:
    return PasswordHasher(security_settings)


def test_hash_is_never_the_plaintext(hasher: PasswordHasher) -> None:
    hashed = hasher.hash(_VALID_PASSWORD)
    assert hashed != _VALID_PASSWORD
    assert _VALID_PASSWORD not in hashed


def test_hash_uses_argon2id(hasher: PasswordHasher) -> None:
    assert hasher.hash(_VALID_PASSWORD).startswith("$argon2id$")


def test_verify_accepts_correct_password(hasher: PasswordHasher) -> None:
    hashed = hasher.hash(_VALID_PASSWORD)
    assert hasher.verify(_VALID_PASSWORD, hashed) is True


def test_verify_rejects_incorrect_password(hasher: PasswordHasher) -> None:
    hashed = hasher.hash(_VALID_PASSWORD)
    assert hasher.verify("wrong-password", hashed) is False


def test_two_hashes_of_the_same_password_differ(hasher: PasswordHasher) -> None:
    """Argon2 salts automatically — two hashes of the same input must
    not be equal, or a database leak would let an attacker spot
    identical passwords across accounts.
    """
    assert hasher.hash(_VALID_PASSWORD) != hasher.hash(_VALID_PASSWORD)


def test_needs_rehash_is_false_for_current_parameters(hasher: PasswordHasher) -> None:
    assert hasher.needs_rehash(hasher.hash(_VALID_PASSWORD)) is False


def test_needs_rehash_is_true_after_a_cost_parameter_increase(
    security_settings: SecuritySettings,
) -> None:
    weak_hasher = PasswordHasher(
        security_settings.model_copy(update={"password_hash_time_cost": 1})
    )
    hashed = weak_hasher.hash(_VALID_PASSWORD)

    stronger_hasher = PasswordHasher(
        security_settings.model_copy(update={"password_hash_time_cost": 4})
    )
    assert stronger_hasher.needs_rehash(hashed) is True


def test_verify_rejects_a_corrupted_hash(hasher: PasswordHasher) -> None:
    with pytest.raises(ValidationException):
        hasher.verify(_VALID_PASSWORD, "not-a-real-argon2-hash")


class TestPasswordPolicy:
    def test_accepts_a_compliant_password(
        self, security_settings: SecuritySettings
    ) -> None:
        validate_password_policy(_VALID_PASSWORD, security_settings)  # must not raise

    def test_rejects_too_short(self, security_settings: SecuritySettings) -> None:
        with pytest.raises(ValidationException, match="characters"):
            validate_password_policy("Sh0rt!", security_settings)

    def test_rejects_missing_uppercase(
        self, security_settings: SecuritySettings
    ) -> None:
        with pytest.raises(ValidationException, match="uppercase"):
            validate_password_policy("correcthorse123!", security_settings)

    def test_rejects_missing_lowercase(
        self, security_settings: SecuritySettings
    ) -> None:
        with pytest.raises(ValidationException, match="lowercase"):
            validate_password_policy("CORRECTHORSE123!", security_settings)

    def test_rejects_missing_digit(self, security_settings: SecuritySettings) -> None:
        with pytest.raises(ValidationException, match="digit"):
            validate_password_policy("CorrectHorseBattery!", security_settings)

    def test_rejects_missing_special_character(
        self, security_settings: SecuritySettings
    ) -> None:
        with pytest.raises(ValidationException, match="special character"):
            validate_password_policy("CorrectHorse123", security_settings)

    def test_reports_every_violation_at_once(
        self, security_settings: SecuritySettings
    ) -> None:
        with pytest.raises(ValidationException) as exc_info:
            validate_password_policy("weak", security_settings)
        violations = exc_info.value.context["violations"]
        assert len(violations) == 4  # length, uppercase, digit, special (has lowercase)

    def test_policy_is_configurable(self, security_settings: SecuritySettings) -> None:
        relaxed = security_settings.model_copy(
            update={
                "password_min_length": 4,
                "password_require_uppercase": False,
                "password_require_lowercase": False,
                "password_require_digit": False,
                "password_require_special": False,
            }
        )
        validate_password_policy(
            "weak", relaxed
        )  # must not raise under a relaxed policy
