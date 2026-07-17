"""UUID generation for request-tracking identifiers.

Centralized so every call site (Request ID middleware, Correlation ID
middleware, future entity IDs) uses the same version and format rather
than each choosing ``uuid4()`` vs. ``uuid1()`` independently.
"""

import uuid


def generate_request_id() -> str:
    """A UUIDv4 string, per
    docs/architecture/specification/81_API_Standards.md's Request ID
    requirement.
    """
    return str(uuid.uuid4())


def generate_correlation_id() -> str:
    """A UUIDv4 string. Distinct function from
    :func:`generate_request_id` even though the implementation is
    identical today, because Correlation ID and Request ID are distinct
    concepts (client-supplied-or-generated vs. always server-generated)
    that may diverge in format in the future — see
    docs/architecture/specification/81_API_Standards.md's Definitions.
    """
    return str(uuid.uuid4())
