"""HTTP response shapes for the API Version Registry — see
cerebrum.api.versions.
"""

from cerebrum.api.schemas.base import APIModel
from cerebrum.api.versions import VersionStatus


class APIVersionResponse(APIModel):
    version: str
    prefix: str
    status: VersionStatus
    deprecation_notice: str | None = None
    migration_guide_url: str | None = None


class APIVersionListResponse(APIModel):
    versions: list[APIVersionResponse]
