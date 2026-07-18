"""Password hashing (Argon2id) and password policy validation.

Argon2id — not bcrypt — is this codebase's choice between CIS Phase 1
Prompt 5's two named options: it is the Password Hashing Competition
winner and OWASP's current first recommendation, with no 72-byte input
truncation footgun (bcrypt silently ignores any password bytes past 72).
"""

import re

from argon2 import PasswordHasher as Argon2PasswordHasher
from argon2 import exceptions as argon2_exceptions

from cerebrum.config.security import SecuritySettings
from cerebrum.shared.errors.exceptions import ValidationException


class PasswordHasher:
    """Wraps ``argon2-cffi`` — never imported directly outside this
    module, per cerebrum.infrastructure.security's package docstring.
    """

    def __init__(self, settings: SecuritySettings) -> None:
        self._hasher = Argon2PasswordHasher(
            time_cost=settings.password_hash_time_cost,
            memory_cost=settings.password_hash_memory_cost_kib,
            parallelism=settings.password_hash_parallelism,
        )

    def hash(self, plaintext_password: str) -> str:
        """Never store the return value's input anywhere else — this is
        the one and only place a plaintext password is read, per CIS
        Phase 1 Prompt 5's "Never store plaintext passwords" rule.
        """
        return self._hasher.hash(plaintext_password)

    def verify(self, plaintext_password: str, hashed_password: str) -> bool:
        """``True`` iff ``plaintext_password`` matches the hash. Never
        raises on a mismatch — a wrong password is an expected outcome,
        not an exceptional one; only a structurally invalid stored hash
        (data corruption) propagates, wrapped as
        :class:`~cerebrum.shared.errors.exceptions.ValidationException`.
        """
        try:
            return self._hasher.verify(hashed_password, plaintext_password)
        except argon2_exceptions.VerifyMismatchError:
            return False
        except argon2_exceptions.InvalidHashError as exc:
            raise ValidationException(
                "Stored password hash is not a valid Argon2 hash.", cause=exc
            ) from exc

    def needs_rehash(self, hashed_password: str) -> bool:
        """``True`` if ``hashed_password`` was produced with different
        parameters than this instance's current configuration — e.g.
        after an operator raises ``SECURITY_PASSWORD_HASH_TIME_COST``.
        The caller (see cerebrum.application.auth.authentication_service)
        re-hashes and persists the new hash on the next successful
        login, migrating the parameter change gradually rather than
        requiring every user to reset their password.
        """
        return self._hasher.check_needs_rehash(hashed_password)


# Password policy validation is a pure function, not a method on
# PasswordHasher: it never touches Argon2 and has no reason to require
# a settings-bound instance to be constructed just to check a string.
_SPECIAL_CHARACTERS = re.compile(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]")


def validate_password_policy(
    plaintext_password: str, settings: SecuritySettings
) -> None:
    """Raises :class:`~cerebrum.shared.errors.exceptions.ValidationException`
    with every violated rule listed in one message, rather than stopping
    at the first failure — so a caller sees the complete policy in one
    round-trip instead of fixing violations one at a time.
    """
    violations: list[str] = []

    if len(plaintext_password) < settings.password_min_length:
        violations.append(f"at least {settings.password_min_length} characters")
    if settings.password_require_uppercase and not any(
        c.isupper() for c in plaintext_password
    ):
        violations.append("an uppercase letter")
    if settings.password_require_lowercase and not any(
        c.islower() for c in plaintext_password
    ):
        violations.append("a lowercase letter")
    if settings.password_require_digit and not any(
        c.isdigit() for c in plaintext_password
    ):
        violations.append("a digit")
    if settings.password_require_special and not _SPECIAL_CHARACTERS.search(
        plaintext_password
    ):
        violations.append("a special character")

    if violations:
        raise ValidationException(
            "Password does not meet policy requirements: must contain "
            + ", ".join(violations)
            + ".",
            context={"violations": violations},
        )
