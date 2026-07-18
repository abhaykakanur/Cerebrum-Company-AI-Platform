"""The shared error taxonomy: :class:`PlatformException` and its
category-specific subclasses.

Every custom exception raised anywhere in Cerebrum SHALL inherit from
``PlatformException`` rather than propagating a bare framework exception —
see docs/architecture/specification/38_Observability.md's Error Taxonomy.
This subpackage is part of the shared kernel: it has no dependency on
application/, infrastructure/, or any other layer, so every layer may
depend on it.
"""

from cerebrum.shared.errors.base import (
    ErrorCategory,
    ErrorSeverity,
    PlatformException,
)
from cerebrum.shared.errors.exceptions import (
    AuthenticationException,
    AuthorizationException,
    ConfigurationException,
    ConnectionException,
    ExpiredTokenException,
    InfrastructureException,
    InvalidTokenException,
    PermissionDeniedException,
    RateLimitExceededException,
    TimeoutException,
    ValidationException,
)

__all__ = [
    "ErrorCategory",
    "ErrorSeverity",
    "PlatformException",
    "ValidationException",
    "ConfigurationException",
    "InfrastructureException",
    "ConnectionException",
    "TimeoutException",
    "AuthenticationException",
    "InvalidTokenException",
    "ExpiredTokenException",
    "AuthorizationException",
    "PermissionDeniedException",
    "RateLimitExceededException",
]
