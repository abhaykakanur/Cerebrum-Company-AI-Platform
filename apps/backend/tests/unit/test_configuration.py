"""Proves the acceptance criteria "Typed configuration validates" from
CIS Phase 1 Prompt 3, and docs/architecture/specification/37_Configuration_Strategy.md's
"no invalid configuration may allow the application to start" rule.
"""

import pytest
from pydantic import ValidationError

from cerebrum.config.environment import Environment
from cerebrum.config.security import SecuritySettings
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


def _set_production_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every credential CIS Phase 1 Prompt 7's ``_reject_default_secrets``
    rejects at its local-development placeholder — set to a
    plausible-looking rotated value so a test can isolate one specific
    still-default variable instead of always tripping on
    ``POSTGRES_PASSWORD`` first.
    """
    monkeypatch.setenv("POSTGRES_PASSWORD", "prod-postgres-secret")
    monkeypatch.setenv("REDIS_PASSWORD", "prod-redis-secret")
    monkeypatch.setenv("NEO4J_PASSWORD", "prod-neo4j-secret")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "prod-minio-access-key")
    monkeypatch.setenv("MINIO_SECRET_KEY", "prod-minio-secret-key")
    monkeypatch.setenv("JWT_SIGNING_SECRET", "prod-jwt-signing-secret")


def test_production_accepts_explicit_hosts_and_origins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECURITY_TRUSTED_HOSTS", "app.cerebrum.example")
    monkeypatch.setenv("SECURITY_CORS_ALLOWED_ORIGINS", "https://app.cerebrum.example")
    _set_production_secrets(monkeypatch)
    built = Settings()
    assert built.security.trusted_hosts == ["app.cerebrum.example"]


@pytest.mark.parametrize(
    "env_var",
    [
        "POSTGRES_PASSWORD",
        "REDIS_PASSWORD",
        "NEO4J_PASSWORD",
        "MINIO_ACCESS_KEY",
        "MINIO_SECRET_KEY",
        "JWT_SIGNING_SECRET",
    ],
)
def test_production_rejects_each_default_secret_placeholder(
    monkeypatch: pytest.MonkeyPatch, env_var: str
) -> None:
    """Every one of the six credentials sharing the
    ``changeme-local-only`` local-development default is individually
    rejected in production — not just the first one checked.
    """
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECURITY_TRUSTED_HOSTS", "app.cerebrum.example")
    monkeypatch.setenv("SECURITY_CORS_ALLOWED_ORIGINS", "https://app.cerebrum.example")
    _set_production_secrets(monkeypatch)
    monkeypatch.delenv(env_var, raising=False)  # falls back to its placeholder default

    with pytest.raises(ConfigurationException, match=env_var):
        Settings()


def test_testing_environment_tolerates_default_secrets(settings: Settings) -> None:
    """The placeholder-rejection rule is production-like-only — the
    ``settings`` fixture (environment=testing) already runs with every
    default secret untouched, and must keep working.
    """
    assert settings.postgres.password.get_secret_value() == "changeme-local-only"


def test_invalid_port_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BACKEND_PORT", "99999")
    with pytest.raises(ValidationError):
        Settings()


def test_jwt_algorithm_rejects_none() -> None:
    """The classic JWT "alg: none" misconfiguration — see
    cerebrum.config.security.SecuritySettings's
    ``_jwt_algorithm_must_be_a_known_safe_signing_algorithm`` validator.
    """
    with pytest.raises(ValidationError, match="jwt_algorithm"):
        SecuritySettings(jwt_algorithm="none")


def test_jwt_algorithm_rejects_an_unimplemented_algorithm_name() -> None:
    with pytest.raises(ValidationError, match="jwt_algorithm"):
        SecuritySettings(jwt_algorithm="not-a-real-algorithm")


@pytest.mark.parametrize("algorithm", ["HS256", "HS384", "HS512", "RS256", "ES256"])
def test_jwt_algorithm_accepts_known_safe_algorithms(algorithm: str) -> None:
    assert SecuritySettings(jwt_algorithm=algorithm).jwt_algorithm == algorithm
