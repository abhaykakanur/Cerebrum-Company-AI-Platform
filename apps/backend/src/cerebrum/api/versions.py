"""The API Version Registry — the authoritative, in-process list of every
API major version this backend serves and each one's lifecycle status.
See docs/architecture/specification/81_API_Standards.md's API Versioning
section (Major Versions, Deprecation Policy, Migration Documentation).

Distinct from :class:`~cerebrum.config.api.APISettings`: that module says
where ``v1`` is *mounted* (``api_v1_prefix``); this module says what
versions *exist* and their status — the registry a client (or a future
version-negotiation middleware) consults to discover what's available and
what's deprecated, independent of any single version's URL prefix.
"""

from dataclasses import dataclass
from enum import StrEnum


class VersionStatus(StrEnum):
    """A version's place in the Deprecation Policy lifecycle — see this
    module's docstring.
    """

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    SUNSET = "sunset"


@dataclass(frozen=True, slots=True)
class APIVersion:
    """One entry in :data:`API_VERSION_REGISTRY`."""

    version: str
    prefix: str
    status: VersionStatus
    deprecation_notice: str | None = None
    """Set once ``status`` becomes :attr:`VersionStatus.DEPRECATED` — the
    human-readable notice surfaced to clients, per the Deprecation
    Policy's requirement that a defined window exist between notice and
    removal (the exact window length is Deferred to Architecture, per
    Open Question 36 in 40_Open_Questions.md).
    """
    migration_guide_url: str | None = None
    """Migration Documentation for this version's eventual successor —
    unset while this is the only/latest version.
    """


API_VERSION_REGISTRY: tuple[APIVersion, ...] = (
    APIVersion(version="v1", prefix="/api/v1", status=VersionStatus.ACTIVE),
)
"""Append, never mutate or remove, an entry when a new major version
ships — see this module's docstring's Migration Documentation note. A
version transitions ACTIVE -> DEPRECATED -> SUNSET in place by editing
its ``status`` (and setting ``deprecation_notice``), never by deleting
the entry: a removed entry would make :func:`get_version` unable to
explain to a client why a version it remembers no longer resolves.
"""


def get_active_versions() -> tuple[APIVersion, ...]:
    """Every version not yet sunset — what a client should be told is
    usable, as opposed to the full historical registry.
    """
    return tuple(
        v for v in API_VERSION_REGISTRY if v.status is not VersionStatus.SUNSET
    )


def get_version(version: str) -> APIVersion | None:
    return next((v for v in API_VERSION_REGISTRY if v.version == version), None)
