"""OpenAPI schema customization.

Adds the environment name into the generated schema's ``info`` block and
caches the result, following FastAPI's documented custom-OpenAPI pattern
— see https://fastapi.tiangolo.com/how-to/extending-openapi/. Kept
deliberately minimal at this milestone: no security schemes are declared
because no Authentication domain exists yet (see this milestone's
Non-Objectives); a future phase adds the Access Token security scheme
here, in this one place, when it exists.
"""

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from cerebrum.config.settings import Settings


def configure_openapi(app: FastAPI, settings: Settings) -> None:
    """Installs a custom ``app.openapi()`` that tags the schema with the
    running environment and caches the result on ``app.openapi_schema``.
    """

    def _custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            tags=app.openapi_tags,
        )
        schema["info"]["x-environment"] = settings.application.environment.value
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = _custom_openapi  # type: ignore[method-assign]
