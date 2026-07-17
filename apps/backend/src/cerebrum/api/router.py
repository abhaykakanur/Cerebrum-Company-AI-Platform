"""The top-level API router: aggregates every sub-router this package
defines. cerebrum.core.routers mounts exactly this one router onto the
FastAPI application — no other module calls ``app.include_router``.
"""

from fastapi import APIRouter

from cerebrum.api.health import router as health_router
from cerebrum.api.v1.router import router as v1_router

router = APIRouter()
router.include_router(health_router)
router.include_router(v1_router)
