"""Application and API metadata: the ``FastAPI(...)`` constructor
keyword arguments, assembled in one place so title/version/docs-URL
policy is never duplicated between the factory and any other module.
"""

from typing import Any

from cerebrum.config.settings import Settings


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
    }
