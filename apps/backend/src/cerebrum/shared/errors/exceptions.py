"""Concrete, category-specific exceptions used by the platform layer built
in this milestone.

Only the categories this milestone's code actually raises are given
concrete subclasses here — Security, Connector, AI, Storage, and Search
errors belong to future feature work (authentication, connectors, AI
reasoning, business repositories, search) and will gain their own
subclasses alongside that work, per
docs/architecture/specification/38_Observability.md's Error Taxonomy.
"""

from typing import Any

from cerebrum.shared.errors.base import ErrorCategory, ErrorSeverity, PlatformException


class ValidationException(PlatformException):
    """Input fails structural or business-rule validation before any
    state change is attempted. Never retried automatically — see
    docs/architecture/specification/38_Observability.md's Error Taxonomy.
    """

    category = ErrorCategory.VALIDATION
    http_status = 422

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        context: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            severity=ErrorSeverity.LOW,
            retryable=False,
            context=context,
            cause=cause,
        )


class ConfigurationException(PlatformException):
    """Configuration failed validation, or a required value is missing —
    per docs/architecture/specification/37_Configuration_Strategy.md's
    "no invalid configuration may allow the application to start" rule.
    Always fatal: retrying without fixing the configuration cannot succeed.
    """

    category = ErrorCategory.CONFIGURATION
    http_status = 500

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        context: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            severity=ErrorSeverity.CRITICAL,
            retryable=False,
            context=context,
            cause=cause,
        )


class InfrastructureException(PlatformException):
    """A failure interacting with underlying infrastructure (a datastore
    connection, an external process) that is not yet further classified
    into Storage/Connector/Search per the full taxonomy. Retryable by
    default — most infrastructure failures at this level are transient.
    """

    category = ErrorCategory.INFRASTRUCTURE
    http_status = 503

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        retryable: bool = True,
        context: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            severity=ErrorSeverity.HIGH,
            retryable=retryable,
            context=context,
            cause=cause,
        )


class ConnectionException(InfrastructureException):
    """An infrastructure client could not establish or maintain a
    connection to its backing service (PostgreSQL, Redis, Neo4j, Qdrant,
    MinIO, OpenSearch). Raised by cerebrum.infrastructure client managers
    in place of the underlying driver's own exception type — see CIS
    Phase 1 Prompt 4's "never leak driver exceptions" rule.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        context: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message, error_code=error_code, retryable=True, context=context, cause=cause
        )


class TimeoutException(InfrastructureException):
    """An infrastructure operation did not complete within its configured
    timeout (see cerebrum.config.infrastructure.InfrastructureSettings).
    Distinct from :class:`ConnectionException`: the service may be
    reachable but slow, rather than unreachable.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        context: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message, error_code=error_code, retryable=True, context=context, cause=cause
        )
