"""Proves CIS Phase 1 Prompt 7's Security Review ("Logging safety")
finding: cerebrum.core.logging's structlog redaction processor performs
a substring — not exact — match, per its own docstring, so a field name
that merely *contains* a denylisted term (``hashed_password``,
``raw_api_key``) is redacted the same as an exact match, without
requiring the denylist to enumerate every variant.
"""

import pytest

from cerebrum.core.logging import _REDACTED_VALUE, _redact_sensitive_fields

pytestmark = pytest.mark.unit


def _redact(**fields: object) -> dict[str, object]:
    return _redact_sensitive_fields(None, "info", dict(fields))


def test_exact_sensitive_field_name_is_redacted() -> None:
    result = _redact(password="hunter2")
    assert result["password"] == _REDACTED_VALUE


@pytest.mark.parametrize(
    "field_name",
    ["hashed_password", "user_password", "raw_api_key", "client_secret", "auth_token"],
)
def test_field_name_containing_a_sensitive_term_is_redacted(field_name: str) -> None:
    result = _redact(**{field_name: "some-sensitive-value"})
    assert result[field_name] == _REDACTED_VALUE


def test_redaction_is_case_insensitive() -> None:
    result = _redact(**{"Authorization": "Bearer xyz", "PASSWORD": "hunter2"})
    assert result["Authorization"] == _REDACTED_VALUE
    assert result["PASSWORD"] == _REDACTED_VALUE


def test_non_sensitive_fields_are_left_untouched() -> None:
    result = _redact(user_id="abc-123", status_code=200, method="GET")
    assert result == {"user_id": "abc-123", "status_code": 200, "method": "GET"}


def test_mixed_event_dict_only_redacts_sensitive_keys() -> None:
    result = _redact(user_id="abc-123", access_token="eyJ...", event="login.success")
    assert result["user_id"] == "abc-123"
    assert result["event"] == "login.success"
    assert result["access_token"] == _REDACTED_VALUE
