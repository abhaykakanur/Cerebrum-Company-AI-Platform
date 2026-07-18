"""HTTP response shape for a completed file upload — the presentation-layer
adapter of :class:`~cerebrum.infrastructure.storage.files.UploadedFile`,
per the File Foundation (CIS Phase 1 Prompt 6). No upload/download route
exists yet — this schema exists so the first feature that adds one has a
settled shape to return rather than inventing its own.
"""

from cerebrum.api.schemas.base import APIModel


class UploadedFileResponse(APIModel):
    object_key: str
    filename: str
    content_type: str
    size_bytes: int
