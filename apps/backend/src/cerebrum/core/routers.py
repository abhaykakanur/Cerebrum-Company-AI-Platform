"""Router registration — mounts cerebrum.api.router.router, the single
top-level API router, onto the application. No other module calls
``app.include_router``.
"""

from fastapi import FastAPI

from cerebrum.api.router import router as api_router


def register_routers(app: FastAPI) -> None:
    app.include_router(api_router)
