"""Concrete, category-specific exceptions used by the platform layer built
in this milestone.

Only the categories this milestone's code actually raises are given
concrete subclasses here — Connector, AI, Storage, and Search errors
belong to future feature work (connectors, AI reasoning, business
repositories, search) and will gain their own subclasses alongside that
work, per docs/architecture/specification/38_Observability.md's Error
Taxonomy. Security errors (authentication/authorization) are added below
as of CIS Phase 1 Prompt 5.
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


class AuthenticationException(PlatformException):
    """The caller's claimed identity could not be established — missing,
    malformed, or incorrect credentials. Never retryable: retrying with
    the same credentials cannot change the outcome. Per
    docs/architecture/specification/38_Observability.md's Security Error
    handling rule, every instance is also recorded as an audit event
    (see cerebrum.application.auth.audit_service) regardless of the
    response's leakage policy.
    """

    category = ErrorCategory.SECURITY
    http_status = 401

    def __init__(
        self,
        message: str = "Authentication failed.",
        *,
        error_code: str | None = None,
        context: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            severity=ErrorSeverity.MEDIUM,
            retryable=False,
            context=context,
            cause=cause,
        )


class InvalidTokenException(AuthenticationException):
    """A JWT failed structural or signature validation — malformed,
    wrong algorithm, or signed with a different key. Distinct from
    :class:`ExpiredTokenException`: this token was never valid, as
    opposed to one that was valid and has since lapsed.
    """

    def __init__(
        self,
        message: str = "Invalid token.",
        *,
        context: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message, context=context, cause=cause)


class ExpiredTokenException(AuthenticationException):
    """A JWT was well-formed and correctly signed but its ``exp`` claim
    has passed. The client's remedy is to use the refresh flow (or
    re-authenticate, if the refresh token has also expired) — not to
    retry the same request.
    """

    def __init__(
        self,
        message: str = "Token has expired.",
        *,
        context: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message, context=context, cause=cause)


class AuthorizationException(PlatformException):
    """An authenticated caller's identity is known but the requested
    action is not permitted. Distinct from :class:`AuthenticationException`
    (who are you?) — this is "I know who you are, and the answer is no."
    """

    category = ErrorCategory.SECURITY
    http_status = 403

    def __init__(
        self,
        message: str = "Not authorized.",
        *,
        error_code: str | None = None,
        context: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            severity=ErrorSeverity.MEDIUM,
            retryable=False,
            context=context,
            cause=cause,
        )


class PermissionDeniedException(AuthorizationException):
    """A specific RBAC permission check failed — see
    cerebrum.application.auth.authorization_service. Carries the
    permission code and scope in ``context`` so an audit event and a
    debug log both have enough detail to explain the denial, independent
    of what the response body is allowed to reveal (leakage policy is
    Deferred to Architecture — see
    docs/architecture/specification/40_Open_Questions.md, Open Question 19).
    """

    def __init__(
        self,
        message: str = "Permission denied.",
        *,
        permission_code: str | None = None,
        context: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        merged_context = {**(context or {})}
        if permission_code is not None:
            merged_context["permission_code"] = permission_code
        super().__init__(message, context=merged_context, cause=cause)


class RateLimitExceededException(PlatformException):
    """A caller exceeded a configured rate limit — see
    cerebrum.infrastructure.security.rate_limiter, currently applied to
    the login endpoint (CIS Phase 1 Prompt 5's "Rate limiting
    foundation"). Retryable — the correct client behavior is to wait out
    ``retry_after_seconds``, not abandon the request.
    """

    category = ErrorCategory.SECURITY
    http_status = 429

    def __init__(
        self,
        message: str = "Too many requests.",
        *,
        retry_after_seconds: int,
        context: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            retryable=True,
            context={**(context or {}), "retry_after_seconds": retry_after_seconds},
            cause=cause,
        )
