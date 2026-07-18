"""The ``/api/v1`` router. Future domain routers are included here — see
this package's ``__init__.py``.
"""

from fastapi import APIRouter

from cerebrum.api.openapi_responses import STANDARD_ERROR_RESPONSES
from cerebrum.api.v1.auth import router as auth_router
from cerebrum.api.v1.collections import router as collections_router
from cerebrum.api.v1.documents import router as documents_router
from cerebrum.api.v1.folders import router as folders_router
from cerebrum.api.v1.labels import router as labels_router
from cerebrum.api.v1.organizations import router as organizations_router
from cerebrum.api.v1.processing_jobs import router as processing_jobs_router
from cerebrum.api.v1.tags import router as tags_router
from cerebrum.api.v1.workspaces import router as workspaces_router
from cerebrum.config.settings import get_settings

router = APIRouter(
    prefix=get_settings().api.api_v1_prefix,
    tags=["API v1"],
    responses=STANDARD_ERROR_RESPONSES,
)
router.include_router(auth_router)
router.include_router(organizations_router)
router.include_router(workspaces_router)
router.include_router(folders_router)
router.include_router(documents_router)
router.include_router(tags_router)
router.include_router(labels_router)
router.include_router(collections_router)
router.include_router(processing_jobs_router)


@router.get("/")
async def api_v1_root() -> dict[str, str]:
    """Confirms the versioned API surface is mounted and reachable."""
    settings = get_settings()
    return {
        "message": "Cerebrum API v1.",
        "version": settings.application.version,
    }
