"""Exposes the API Version Registry over HTTP — see cerebrum.api.versions.

Mounted at the application root (``/api/versions``), not under any single
version's own prefix: a client must be able to discover which versions
exist before committing to one, mirroring cerebrum.api.health's rationale
for living outside ``/api/v1``.
"""

from fastapi import APIRouter

from cerebrum.api.schemas.versions import APIVersionListResponse, APIVersionResponse
from cerebrum.api.versions import get_active_versions

router = APIRouter(tags=["Versioning"])


@router.get("/api/versions", response_model=APIVersionListResponse)
async def list_api_versions() -> APIVersionListResponse:
    """Every API major version this backend currently serves — sunset
    versions are omitted; see cerebrum.api.versions.get_active_versions.
    """
    return APIVersionListResponse(
        versions=[
            APIVersionResponse(
                version=v.version,
                prefix=v.prefix,
                status=v.status,
                deprecation_notice=v.deprecation_notice,
                migration_guide_url=v.migration_guide_url,
            )
            for v in get_active_versions()
        ]
    )
