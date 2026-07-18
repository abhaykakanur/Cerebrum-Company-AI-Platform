"""Proves CIS Phase 1 Prompt 6's File Foundation acceptance criterion:
reusable upload validation exists and rejects each documented violation
— see cerebrum.infrastructure.storage.files. No document ingestion or
concrete storage adapter is under test here; none exists yet.
"""

import pytest

from cerebrum.infrastructure.storage.files import FileValidationPolicy, validate_file
from cerebrum.shared.errors.exceptions import ValidationException

pytestmark = pytest.mark.unit

_POLICY = FileValidationPolicy(
    max_size_bytes=1024,
    allowed_content_types=frozenset({"text/plain", "application/pdf"}),
)


def test_valid_file_passes() -> None:
    validate_file(
        filename="notes.txt", content_type="text/plain", size_bytes=100, policy=_POLICY
    )  # must not raise


def test_rejects_empty_filename() -> None:
    with pytest.raises(ValidationException):
        validate_file(
            filename="   ", content_type="text/plain", size_bytes=100, policy=_POLICY
        )


def test_rejects_zero_size() -> None:
    with pytest.raises(ValidationException):
        validate_file(
            filename="notes.txt",
            content_type="text/plain",
            size_bytes=0,
            policy=_POLICY,
        )


def test_rejects_oversized_file() -> None:
    with pytest.raises(ValidationException):
        validate_file(
            filename="notes.txt",
            content_type="text/plain",
            size_bytes=2000,
            policy=_POLICY,
        )


def test_rejects_disallowed_content_type() -> None:
    with pytest.raises(ValidationException):
        validate_file(
            filename="notes.exe",
            content_type="application/x-msdownload",
            size_bytes=100,
            policy=_POLICY,
        )


def test_any_content_type_accepted_when_policy_allows_all() -> None:
    policy = FileValidationPolicy(max_size_bytes=1024, allowed_content_types=None)
    validate_file(
        filename="anything.bin",
        content_type="application/octet-stream",
        size_bytes=100,
        policy=policy,
    )  # must not raise
