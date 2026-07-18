"""Application and API metadata: the ``FastAPI(...)`` constructor
keyword arguments, assembled in one place so title/version/docs-URL
policy is never duplicated between the factory and any other module.
"""

from enum import Enum
from typing import Any

from fastapi.routing import APIRoute

from cerebrum.config.settings import Settings

# CIS Phase 1 Prompt 6's OpenAPI "Tags" requirement: a description for
# every tag used across api/, surfaced in Swagger UI/ReDoc's navigation
# rather than left as a bare, undocumented label. A router's own routes
# still supply their per-operation description via each function's
# docstring — see e.g. cerebrum.api.health, cerebrum.api.v1.auth.
OPENAPI_TAGS: list[dict[str, str]] = [
    {
        "name": "Health",
        "description": "Liveness, readiness, and detailed health — "
        "process-orchestration signals, unversioned and unauthenticated.",
    },
    {
        "name": "Versioning",
        "description": "The API Version Registry — which major versions this backend "
        "serves and their lifecycle status.",
    },
    {
        "name": "API v1",
        "description": "The ``/api/v1`` versioned public API surface.",
    },
    {
        "name": "Authentication",
        "description": "Login, token refresh, logout, and the current-user endpoint. "
        "See docs/architecture/security/authentication-guide.md.",
    },
]


def _generate_operation_id(route: APIRoute) -> str:
    """Operation IDs are ``<tag>.<route_name>`` (e.g. ``authentication.login``)
    rather than FastAPI's default (a mangled ``function_name path_params``
    string) — CIS Phase 1 Prompt 6's OpenAPI "Operation IDs" requirement.
    Short, stable, and what a generated client SDK would want as its
    method name, per docs/architecture/specification/80_API_Architecture.md's
    "Future SDK APIs" category.

    Uses the LAST tag, not the first: ``APIRouter.include_router`` prepends
    a parent router's own tags (e.g. ``"API v1"``) ahead of a nested
    router's more specific ones (e.g. ``"Authentication"``) in
    ``route.tags`` — the last tag is consistently the most specific one a
    route was declared with.
    """
    if not route.tags:
        return f"default.{route.name}"
    raw_tag = route.tags[-1]
    # FastAPI types a tag as `str | Enum` (a route may be tagged with an
    # Enum member); normalize to its string value either way.
    tag_name = raw_tag.value if isinstance(raw_tag, Enum) else raw_tag
    return f"{tag_name.lower().replace(' ', '_')}.{route.name}"


def build_application_metadata(settings: Settings) -> dict[str, Any]:
    """Keyword arguments for the ``FastAPI`` constructor.

    Interactive docs (``/docs``, ``/redoc``) and the raw OpenAPI schema
    are disabled in production-like environments — exposing the full API
    surface and schema publicly is an unnecessary information-disclosure
    concern once real endpoints exist (see
    docs/architecture/specification/79_Threat_Model.md), and there is no
    reason to accept that risk before it is needed.
    """
    docs_enabled = not settings.application.environment.is_production_like
    return {
        "title": settings.application.name,
        "version": settings.application.version,
        "description": (
            "Cerebrum — Enterprise Knowledge Intelligence Platform API. "
            "See docs/architecture/specification/80_API_Architecture.md."
        ),
        "openapi_url": (
            f"{settings.api.api_v1_prefix}/openapi.json" if docs_enabled else None
        ),
        "docs_url": f"{settings.api.api_v1_prefix}/docs" if docs_enabled else None,
        "redoc_url": f"{settings.api.api_v1_prefix}/redoc" if docs_enabled else None,
        "debug": settings.application.debug,
        "openapi_tags": OPENAPI_TAGS,
        "generate_unique_id_function": _generate_operation_id,
    }
