"""The Application Factory: the only place responsible for assembling the
backend, per CIS Phase 1 Prompt 3 Section 2. The application SHALL NEVER
be created directly outside this function — see cerebrum.main, whose only
responsibilities are loading configuration, calling this factory, and
starting uvicorn.

``create_application`` performs the synchronous half of the Startup
Pipeline (Load Configuration through Register Background Runtime); the
asynchronous half (Initialize Application State, Infrastructure
Validation) runs in cerebrum.core.lifecycle's lifespan context manager
when the ASGI server actually starts serving.
"""

from fastapi import FastAPI

from cerebrum.config.settings import Settings, get_settings
from cerebrum.core.background import register_background_runtime
from cerebrum.core.exception_handlers import register_exception_handlers
from cerebrum.core.lifecycle import lifespan
from cerebrum.core.logging import configure_logging, get_logger
from cerebrum.core.metadata import build_application_metadata
from cerebrum.core.openapi import configure_openapi
from cerebrum.core.routers import register_routers
from cerebrum.middleware.registry import register_middleware


def create_application(settings: Settings | None = None) -> FastAPI:
    """Builds and returns the fully-assembled FastAPI application.

    Accepts an optional ``settings`` override so tests can construct an
    application against a non-cached :class:`~cerebrum.config.settings.Settings`
    instance (e.g. one built from monkeypatched environment variables)
    without mutating the process-wide cache in
    :func:`~cerebrum.config.settings.get_settings`.
    """
    settings = settings or get_settings()

    # Initialize Logger — before anything else logs.
    configure_logging(settings.logging)
    logger = get_logger("cerebrum.core")
    logger.info("factory.startup_pipeline_begin")

    # Configuration was already validated by Settings' own model
    # validator at construction time (see cerebrum.config.settings) — a
    # Settings instance existing at all means it passed validation.
    logger.info("factory.configuration_validated")

    app = FastAPI(lifespan=lifespan, **build_application_metadata(settings))
    # Stashed so the lifespan context manager — whose signature is fixed
    # to accept only ``app`` — can reach the Settings this factory built
    # the application against.
    app.state.cerebrum_settings = settings

    # Register Middleware
    register_middleware(app, settings)
    logger.info("factory.middleware_registered")

    # Register Exception Handlers
    register_exception_handlers(app)
    logger.info("factory.exception_handlers_registered")

    # Register Routers (includes Health per cerebrum.api.health)
    register_routers(app)
    logger.info("factory.routers_registered")

    # Register OpenAPI
    configure_openapi(app, settings)
    logger.info("factory.openapi_registered")

    # Register Background Runtime
    register_background_runtime(app, settings)

    logger.info(
        "factory.startup_pipeline_complete",
        environment=settings.application.environment.value,
        version=settings.application.version,
    )
    return app
