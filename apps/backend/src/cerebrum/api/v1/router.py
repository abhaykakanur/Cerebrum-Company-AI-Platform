"""The ``/api/v1`` router. Future domain routers are included here — see
this package's ``__init__.py``.
"""

from fastapi import APIRouter

from cerebrum.api.openapi_responses import STANDARD_ERROR_RESPONSES
from cerebrum.api.v1.ai import router as ai_router
from cerebrum.api.v1.auth import router as auth_router
from cerebrum.api.v1.capsules import router as capsules_router
from cerebrum.api.v1.collections import router as collections_router
from cerebrum.api.v1.connectors import router as connectors_router
from cerebrum.api.v1.conversations import router as conversations_router
from cerebrum.api.v1.documents import router as documents_router
from cerebrum.api.v1.entities import router as entities_router
from cerebrum.api.v1.folders import router as folders_router
from cerebrum.api.v1.knowledge_graph import router as knowledge_graph_router
from cerebrum.api.v1.labels import router as labels_router
from cerebrum.api.v1.organizations import router as organizations_router
from cerebrum.api.v1.processing_jobs import router as processing_jobs_router
from cerebrum.api.v1.relationships import router as relationships_router
from cerebrum.api.v1.retrieval import router as retrieval_router
from cerebrum.api.v1.semantic import router as semantic_router
from cerebrum.api.v1.tags import router as tags_router
from cerebrum.api.v1.workflows import router as workflows_router
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
router.include_router(entities_router)
router.include_router(relationships_router)
router.include_router(knowledge_graph_router)
router.include_router(semantic_router)
router.include_router(retrieval_router)
router.include_router(ai_router)
router.include_router(conversations_router)
router.include_router(connectors_router)
router.include_router(workflows_router)
router.include_router(capsules_router)


@router.get("/")
async def api_v1_root() -> dict[str, str]:
    """Confirms the versioned API surface is mounted and reachable."""
    settings = get_settings()
    return {
        "message": "Cerebrum API v1.",
        "version": settings.application.version,
    }
