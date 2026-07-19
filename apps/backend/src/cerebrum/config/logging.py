"""Logging configuration: verbosity and output format.

See docs/architecture/specification/38_Observability.md's Structured
Logging section. This module only defines *settings*; the logging
pipeline itself (processors, redaction, renderers) lives in
cerebrum.core.logging, which reads this settings object once at startup.
"""

from enum import StrEnum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from cerebrum.config import ENV_FILE


class LogLevel(StrEnum):
    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogFormat(StrEnum):
    JSON = "json"
    CONSOLE = "console"


class LoggingSettings(BaseSettings):
    """Minimum log level and output rendering. Read from ``LOG_LEVEL`` and
    ``LOG_FORMAT`` — the only two logging variables without a subsystem
    prefix, per docs/architecture/specification/37_Configuration_Strategy.md.
    """

    model_config = SettingsConfigDict(
        env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )

    log_level: LogLevel = Field(
        default=LogLevel.INFO, description="Minimum severity emitted. LOG_LEVEL."
    )
    log_format: LogFormat = Field(
        default=LogFormat.JSON,
        description="JSON in every real environment; CONSOLE is a local-development "
        "readability convenience only. LOG_FORMAT.",
    )
