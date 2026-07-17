"""Proves the acceptance criteria "Typed configuration validates" from
CIS Phase 1 Prompt 3, and docs/architecture/specification/37_Configuration_Strategy.md's
"no invalid configuration may allow the application to start" rule.
"""

import pytest
from pydantic import ValidationError

from cerebrum.config.environment import Environment
from cerebrum.config.settings import Settings, get_settings
from cerebrum.shared.errors.exceptions import ConfigurationException

pytestmark = pytest.mark.unit


def test_settings_loads_with_defaults(settings: Settings) -> None:
    assert settings.application.environment == Environment.TESTING
    assert settings.api.port == 8000


def test_get_settings_is_cached(settings: Settings) -> None:
    assert get_settings() is get_settings()


def test_production_rejects_wildcard_trusted_hosts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECURITY_TRUSTED_HOSTS", "*")
    monkeypatch.setenv("SECURITY_CORS_ALLOWED_ORIGINS", "https://app.cerebrum.example")
    with pytest.raises(ConfigurationException):
        Settings()


def test_production_rejects_wildcard_cors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECURITY_TRUSTED_HOSTS", "app.cerebrum.example")
    monkeypatch.setenv("SECURITY_CORS_ALLOWED_ORIGINS", "*")
    with pytest.raises(ConfigurationException):
        Settings()


def test_production_accepts_explicit_hosts_and_origins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECURITY_TRUSTED_HOSTS", "app.cerebrum.example")
    monkeypatch.setenv("SECURITY_CORS_ALLOWED_ORIGINS", "https://app.cerebrum.example")
    built = Settings()
    assert built.security.trusted_hosts == ["app.cerebrum.example"]


def test_invalid_port_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BACKEND_PORT", "99999")
    with pytest.raises(ValidationError):
        Settings()
