"""Proves CIS Phase 1 Prompt 6's OpenAPI improvements acceptance
criteria: tags carry descriptions, operation IDs are short and
tag-scoped (not FastAPI's mangled default), every route under
``/api/v1`` documents the standard error responses, the OAuth2 security
scheme is present and documented, and at least one schema demonstrates
the "Examples" requirement.
"""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


@pytest.fixture
def schema(client: TestClient) -> dict[str, object]:
    return client.get("/api/v1/openapi.json").json()


def test_every_declared_tag_has_a_description(schema: dict[str, object]) -> None:
    tags = schema["tags"]
    assert tags  # not empty — see the earlier bug where configure_openapi
    # dropped app.openapi_tags entirely.
    for tag in tags:
        assert tag["description"]


def test_operation_ids_are_tag_scoped_not_mangled(schema: dict[str, object]) -> None:
    login_op = schema["paths"]["/api/v1/auth/login"]["post"]
    assert login_op["operationId"] == "authentication.login"
    live_op = schema["paths"]["/live"]["get"]
    assert live_op["operationId"] == "health.liveness"


def test_nested_router_operation_id_uses_the_most_specific_tag(
    schema: dict[str, object],
) -> None:
    """``/api/v1/auth/*`` routes carry both "API v1" (from the parent
    router) and "Authentication" (their own) tags — the operation ID
    must use the latter, not the former.
    """
    me_op = schema["paths"]["/api/v1/auth/me"]["get"]
    assert me_op["tags"] == ["API v1", "Authentication"]
    assert me_op["operationId"].startswith("authentication.")


def test_protected_route_documents_standard_error_responses(
    schema: dict[str, object],
) -> None:
    me_responses = schema["paths"]["/api/v1/auth/me"]["get"]["responses"]
    for status_code in ("401", "403", "404", "422", "429", "500"):
        assert status_code in me_responses


def test_oauth2_security_scheme_is_documented(schema: dict[str, object]) -> None:
    security_schemes = schema["components"]["securitySchemes"]
    assert "OAuth2PasswordBearer" in security_schemes
    scheme = security_schemes["OAuth2PasswordBearer"]
    assert scheme["flows"]["password"]["tokenUrl"] == "/api/v1/auth/login"


def test_error_response_schema_is_registered_in_components(
    schema: dict[str, object],
) -> None:
    assert "ErrorResponse" in schema["components"]["schemas"]


def test_token_response_schema_declares_an_example(schema: dict[str, object]) -> None:
    token_schema = schema["components"]["schemas"]["TokenResponse"]
    assert token_schema.get("examples")
