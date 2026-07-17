"""The ``/api/v1`` router. Future domain routers are included here — see
this package's ``__init__.py``.
"""

from fastapi import APIRouter

from cerebrum.config.settings import get_settings

router = APIRouter(prefix=get_settings().api.api_v1_prefix, tags=["API v1"])


@router.get("/")
async def api_v1_root() -> dict[str, str]:
    """Confirms the versioned API surface is mounted and reachable. Not a
    business endpoint — no domain routers are registered under this
    prefix yet.
    """
    settings = get_settings()
    return {
        "message": "Cerebrum API v1 — no domain endpoints are implemented yet.",
        "version": settings.application.version,
    }
