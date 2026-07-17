"""The Environment enum: the single definition of which deployment modes
Cerebrum supports. Every environment-conditional decision elsewhere in
the codebase (docs enabled, log format, strict CORS) SHALL branch on this
type, never on a raw string — see
docs/architecture/specification/37_Configuration_Strategy.md.
"""

from enum import StrEnum


class Environment(StrEnum):
    """A deployment mode. Read once, at startup, from the ``ENVIRONMENT``
    environment variable — see :class:`cerebrum.config.application.ApplicationSettings`.
    """

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

    @property
    def is_production_like(self) -> bool:
        """True for environments where production-grade safety defaults
        (no interactive docs, strict CORS, redacted error detail) apply.
        """
        return self in (Environment.STAGING, Environment.PRODUCTION)
