"""The ASGI entrypoint.

Per CIS Phase 1 Prompt 3 Section 2's Application Bootstrap requirement,
this module's only responsibilities are: load configuration, call the
Application Factory, and start uvicorn. No business logic, no route
definitions, no middleware registration — all of that lives in
cerebrum.core.factory.

Run with either:
    uv run uvicorn cerebrum.main:app --reload
    uv run cerebrum          # the console script defined in pyproject.toml
"""

import uvicorn

from cerebrum.config.settings import get_settings
from cerebrum.core.factory import create_application

settings = get_settings()
app = create_application(settings)


def run() -> None:
    """Entrypoint for the ``cerebrum`` console script (see
    apps/backend/pyproject.toml's ``[project.scripts]``).
    """
    uvicorn.run(
        "cerebrum.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=not settings.application.environment.is_production_like,
        # structlog owns logging configuration — see cerebrum.core.logging.
        log_config=None,
    )


if __name__ == "__main__":
    run()
