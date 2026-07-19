"""The provider-independent connector interface — CIS Phase 5 Prompt
1's ``Connector abstraction``. Every concrete adapter in this package
implements :class:`Connector`; nothing outside
cerebrum.infrastructure.connectors imports an adapter-specific SDK or
response shape, only these types — the same Provider Independence
Principle docs/architecture/specification/60_AI_Model_Abstraction.md
states for LLM providers, applied here to enterprise systems.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from pydantic import SecretStr

from cerebrum.infrastructure.database.models.connector import ConnectorAuthType


@dataclass(frozen=True, slots=True)
class ConnectorCredentials:
    """Provider-independent authentication — CIS Phase 5 Prompt 1's
    OAuth2/Personal Access Token/API Key/Service Account support. Each
    concrete adapter documents which ``secrets`` keys it expects (e.g.
    GitHub's Personal Access Token connector reads ``"token"``; Jira's
    API Key connector reads ``"email"``/``"api_token"``) — a thin,
    uniform envelope rather than one dataclass per auth type, since the
    *shape* of "some named secret strings" is the only thing every auth
    type actually shares.

    Every value is wrapped in ``SecretStr`` the moment it is loaded from
    :attr:`~cerebrum.infrastructure.database.models.connector.Connector.credentials`'s
    raw JSON — see :func:`credentials_from_raw` — so a connector
    adapter never holds a bare secret string longer than the single
    ``.get_secret_value()`` call that puts it into an HTTP header.
    """

    auth_type: ConnectorAuthType
    secrets: Mapping[str, SecretStr]

    def get(self, key: str) -> str:
        return self.secrets[key].get_secret_value()


def credentials_from_raw(
    *, auth_type: ConnectorAuthType, raw: Mapping[str, Any]
) -> ConnectorCredentials:
    return ConnectorCredentials(
        auth_type=auth_type,
        secrets={key: SecretStr(str(value)) for key, value in raw.items()},
    )


@dataclass(frozen=True, slots=True)
class ConnectorItem:
    """One normalized unit of external content (a GitHub issue, a
    Confluence page, a Slack message, ...) — CIS Phase 5 Prompt 1's
    Normalization stage output, before it ever reaches the existing
    document pipeline.
    """

    external_id: str
    title: str
    kind: str
    external_url: str | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ConnectorContent:
    content: bytes
    content_type: str
    filename: str


@dataclass(frozen=True, slots=True)
class ConnectorPage:
    """One page of :meth:`Connector.list_changes` results.
    ``next_cursor`` is ``None`` once the source has no more pages for
    this sync run — CIS Phase 5 Prompt 1's Progress Tracking/Resume
    Failed Sync read this back from
    :attr:`~cerebrum.infrastructure.database.models.connector_sync_run.ConnectorSyncRun.cursor`
    to continue a partially-completed run rather than re-scanning
    everything.
    """

    items: list[ConnectorItem]
    next_cursor: str | None = None


class ConnectorError(Exception):
    """Raised when a connector adapter cannot complete a request (a
    non-2xx HTTP response, malformed response body, or network
    failure) — deliberately provider-shape-free, mirroring
    cerebrum.infrastructure.llm.provider.LLMProviderError's identical
    role for LLM adapters.
    """


class Connector(Protocol):
    """CIS Phase 5 Prompt 1's ``Connector`` port. ``connector_type``
    identifies the adapter for logging/events/registry lookup —
    application-layer code never branches on it, only records it.
    """

    connector_type: str

    async def test_connection(
        self, *, credentials: ConnectorCredentials, config: dict[str, Any]
    ) -> bool: ...

    async def list_changes(
        self,
        *,
        credentials: ConnectorCredentials,
        config: dict[str, Any],
        since: datetime | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> ConnectorPage: ...

    async def fetch_content(
        self,
        *,
        credentials: ConnectorCredentials,
        config: dict[str, Any],
        item: ConnectorItem,
    ) -> ConnectorContent: ...
