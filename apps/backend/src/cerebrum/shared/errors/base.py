"""``PlatformException``: the base type every Cerebrum exception inherits
from, and the taxonomy it is classified into.

See docs/architecture/specification/38_Observability.md's Error Handling
Strategy. The eight categories below are exactly that document's Error
Taxonomy table plus the Recoverable/Fatal distinction it defines
immediately after — this module is the executable form of that table, not
a reinterpretation of it.
"""

from enum import StrEnum
from typing import Any


class ErrorCategory(StrEnum):
    """Exactly one category, chosen at the point an error is raised — see
    docs/architecture/specification/38_Observability.md's Error
    Propagation Rule (never inferred later by a generic catch-all).
    """

    VALIDATION = "validation"
    SECURITY = "security"
    CONNECTOR = "connector"
    AI = "ai"
    STORAGE = "storage"
    SEARCH = "search"
    CONFIGURATION = "configuration"
    INFRASTRUCTURE = "infrastructure"
    APPLICATION = "application"
    UNEXPECTED = "unexpected"


class ErrorSeverity(StrEnum):
    """How loudly an error should surface — independent of HTTP status,
    since a 4xx client error and a 5xx server error can each be
    operationally routine or urgent depending on category and volume.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PlatformException(Exception):
    """Base class for every custom exception in Cerebrum.

    Carries everything docs/architecture/specification/38_Observability.md
    requires to classify, log, and translate an error into a standardized
    API response (see cerebrum.core.exception_handlers) without the
    handler needing to inspect exception-subclass-specific attributes.

    Unclassified errors default to :attr:`ErrorSeverity.HIGH` and
    non-retryable — the safe default pending classification per
    Observability's Responsibilities section ("an unclassified error
    defaulting to Fatal is the safe default pending classification, never
    Recoverable by default").
    """

    category: ErrorCategory = ErrorCategory.UNEXPECTED
    http_status: int = 500

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        retryable: bool = False,
        context: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code or type(self).__name__
        self.severity = severity
        self.retryable = retryable
        self.context = context or {}
        self.cause = cause
        if cause is not None:
            self.__cause__ = cause

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(error_code={self.error_code!r}, "
            f"category={self.category.value!r}, http_status={self.http_status})"
        )
