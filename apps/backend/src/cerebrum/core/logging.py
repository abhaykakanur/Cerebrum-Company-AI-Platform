"""Structured logging setup: the Logger Factory referenced throughout CIS
Phase 1 Prompt 3 Section 3.

Configures structlog once, at startup (see cerebrum.core.lifecycle), so
every subsequent ``get_logger(...)`` call anywhere in the codebase — API
handlers, middleware, future workers — shares one processor pipeline:
JSON (or console, in development) rendering, automatic correlation-context
binding, and sensitive-field redaction. No call site configures logging
itself; per docs/architecture/specification/38_Observability.md, every
log entry SHALL be emitted via this shared instrumentation port, never a
bare ``print`` or unstructured string.
"""

import logging
import sys
from typing import Any, cast

import structlog
from structlog.types import EventDict, Processor
from structlog.typing import FilteringBoundLogger

from cerebrum.config.logging import LogFormat, LoggingSettings

# Field names never allowed to reach a log sink in cleartext — see
# CIS Phase 1 Prompt 3 Section 3's Sensitive Data list and
# docs/architecture/specification/38_Observability.md's redaction
# requirement (denylist-based, not developer-discipline-based).
_SENSITIVE_FIELD_NAMES = frozenset(
    {
        "password",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "secret",
        "authorization",
        "cookie",
        "set-cookie",
        "jwt",
        "oauth_token",
        "embedding",
        "embeddings",
        "prompt",
        "llm_response",
        "database_url",
        "dsn",
    }
)
_REDACTED_VALUE = "***REDACTED***"


def _redact_sensitive_fields(
    _logger: object, _method_name: str, event_dict: EventDict
) -> EventDict:
    """A structlog processor: replaces any field whose key matches the
    sensitive-field denylist (case-insensitive substring match) with a
    fixed redaction marker, regardless of value.

    Substring, not exact, match: a call site binding ``hashed_password``,
    ``raw_api_key``, or ``client_secret`` — a plausible field name none of
    this codebase's current call sites happen to use, but not something
    this processor should rely on staying true — is caught by the same
    ``password``/``api_key``/``secret`` entries as the exact field name,
    with no denylist maintenance required for every variant.
    """
    for key in list(event_dict.keys()):
        lowered_key = key.lower()
        if any(sensitive in lowered_key for sensitive in _SENSITIVE_FIELD_NAMES):
            event_dict[key] = _REDACTED_VALUE
    return event_dict


def configure_logging(settings: LoggingSettings) -> None:
    """Configures structlog's global processor chain. Called exactly once,
    from the Application Factory's startup pipeline, before any logger is
    used — see CIS Phase 1 Prompt 3 Section 2's Startup Pipeline
    ("Initialize Logger" stage).
    """
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        _redact_sensitive_fields,
    ]

    renderer: Processor = (
        structlog.processors.JSONRenderer()
        if settings.log_format is LogFormat.JSON
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            _python_log_level(settings.log_level.value)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def _python_log_level(level_name: str) -> int:
    """Maps Cerebrum's LogLevel (which includes TRACE, unknown to the
    standard library) onto a stdlib-compatible integer level.
    """
    if level_name == "trace":
        return 5  # Below DEBUG; structlog's filtering bound logger accepts any int.
    return int(getattr(logging, level_name.upper()))


def get_logger(name: str, **initial_context: Any) -> FilteringBoundLogger:
    """The Logger Factory: every call site obtains its logger through this
    function, never by instantiating structlog directly. ``name``
    conventionally identifies the owning component (see the category
    helpers below), and becomes the ``component`` field on every entry.
    """
    return cast(
        FilteringBoundLogger, structlog.get_logger(component=name, **initial_context)
    )


def get_api_logger() -> FilteringBoundLogger:
    """The API layer's category logger — see CIS Phase 1 Prompt 3 Section
    3's Log Categories.
    """
    return get_logger("cerebrum.api")


def get_application_logger() -> FilteringBoundLogger:
    return get_logger("cerebrum.application")


def get_infrastructure_logger() -> FilteringBoundLogger:
    return get_logger("cerebrum.infrastructure")


def get_worker_logger() -> FilteringBoundLogger:
    return get_logger("cerebrum.workers")


def get_events_logger() -> FilteringBoundLogger:
    return get_logger("cerebrum.events")
