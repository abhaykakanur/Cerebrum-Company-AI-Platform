"""The standard response envelope every Cerebrum API endpoint returns.

Implements docs/architecture/specification/81_API_Standards.md's Response
Standards table (Status, Message, Timestamp, Request ID, Version, Data,
Pagination, Metadata) and its Error Model Cross-Reference (the same
envelope, with ``success=False`` plus Error Code, Details, Documentation
URL, and Retryable). No endpoint SHALL construct an ad hoc response shape
— see that document's Responsibilities section ("a partial implementation
... breaks the Consistency principle for every client").
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from cerebrum.utils.clock import utcnow


class PaginationMeta(BaseModel):
    """Present only on collection-returning endpoints — see
    docs/architecture/specification/81_API_Standards.md's Pagination
    section. No endpoint in this milestone returns a collection; this
    model exists so the first one that does has a settled shape to
    return rather than inventing its own.
    """

    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)
    has_next: bool
    has_previous: bool
    cursor: str | None = Field(
        default=None,
        description="Opaque cursor for Cursor Pagination, per "
        "docs/architecture/specification/81_API_Standards.md's Definitions. "
        "Unset for Offset Pagination.",
    )


class SuccessResponse[DataT](BaseModel):
    """The envelope every successful response is wrapped in."""

    success: Literal[True] = True
    message: str | None = None
    data: DataT
    metadata: dict[str, object] | None = None
    pagination: PaginationMeta | None = None
    timestamp: datetime = Field(default_factory=utcnow)
    request_id: str
    correlation_id: str | None = None
    version: str


class ErrorDetail(BaseModel):
    """One structural or business-rule validation failure. A single error
    response may carry several, e.g. one per invalid field.
    """

    field: str | None = None
    message: str


class ErrorResponse(BaseModel):
    """The envelope every failed response is wrapped in — see
    docs/architecture/specification/81_API_Standards.md's Error Model
    Cross-Reference and docs/architecture/specification/38_Observability.md's
    Error Taxonomy (``error_code`` corresponds to a
    :class:`~cerebrum.shared.errors.base.PlatformException` subclass).
    """

    success: Literal[False] = False
    error_code: str
    message: str
    details: list[ErrorDetail] | None = None
    documentation_url: str | None = None
    retryable: bool = False
    timestamp: datetime = Field(default_factory=utcnow)
    request_id: str
    correlation_id: str | None = None
    version: str
