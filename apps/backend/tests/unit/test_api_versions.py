"""Proves CIS Phase 1 Prompt 6's API Versioning acceptance criteria: a
Version Registry exists, carries lifecycle status, and is reachable over
HTTP — see cerebrum.api.versions/cerebrum.api.version_routes.
"""

import pytest
from fastapi.testclient import TestClient

from cerebrum.api import versions as versions_module
from cerebrum.api.versions import (
    APIVersion,
    VersionStatus,
    get_active_versions,
    get_version,
)

pytestmark = pytest.mark.unit


def test_v1_is_registered_and_active() -> None:
    v1 = get_version("v1")
    assert v1 is not None
    assert v1.status == VersionStatus.ACTIVE
    assert v1.prefix == "/api/v1"


def test_unknown_version_returns_none() -> None:
    assert get_version("v99") is None


def test_get_active_versions_excludes_sunset(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_registry = (
        APIVersion(version="v1", prefix="/api/v1", status=VersionStatus.ACTIVE),
        APIVersion(version="v0", prefix="/api/v0", status=VersionStatus.SUNSET),
    )
    monkeypatch.setattr(versions_module, "API_VERSION_REGISTRY", fake_registry)

    active = get_active_versions()

    assert [v.version for v in active] == ["v1"]


def test_versions_endpoint_lists_active_versions(client: TestClient) -> None:
    response = client.get("/api/versions")
    assert response.status_code == 200
    body = response.json()
    assert body["versions"] == [
        {
            "version": "v1",
            "prefix": "/api/v1",
            "status": "active",
            "deprecation_notice": None,
            "migration_guide_url": None,
        }
    ]
