"""``BitbucketConnector``: a ``Connector`` adapter over the Bitbucket
Cloud REST API (``GET /2.0/repositories/{workspace}/{repo_slug}/issues``)
— see
https://developer.atlassian.com/cloud/bitbucket/rest/api-group-issue-tracker/.
Authenticates with an app password over HTTP Basic auth (Bitbucket
Cloud's Personal-Access-Token equivalent). ``config`` keys:
``workspace``, ``repo_slug``.

Bitbucket's list responses are a ``{"values": [...], "next": url}``
envelope where ``next`` is already a complete, ready-to-call URL — this
adapter stores that URL directly as ``next_cursor`` rather than
re-deriving query parameters, unlike GitHub/GitLab's page-number
cursors.
"""

from datetime import datetime
from typing import Any

import httpx

from cerebrum.infrastructure.connectors._http import request_json
from cerebrum.infrastructure.connectors.base import (
    ConnectorContent,
    ConnectorCredentials,
    ConnectorItem,
    ConnectorPage,
)

_BASE_URL = "https://api.bitbucket.org/2.0"


class BitbucketConnector:
    connector_type = "bitbucket"

    def __init__(self, *, http_client: httpx.AsyncClient) -> None:
        self._client = http_client

    @staticmethod
    def _auth(credentials: ConnectorCredentials) -> tuple[str, str]:
        return credentials.get("username"), credentials.get("app_password")

    async def test_connection(
        self, *, credentials: ConnectorCredentials, config: dict[str, Any]
    ) -> bool:
        await request_json(
            self._client,
            "GET",
            f"{_BASE_URL}/repositories/{config['workspace']}/{config['repo_slug']}",
            auth=self._auth(credentials),
        )
        return True

    async def list_changes(
        self,
        *,
        credentials: ConnectorCredentials,
        config: dict[str, Any],
        since: datetime | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> ConnectorPage:
        if cursor:
            url = cursor
            params = None
        else:
            url = (
                f"{_BASE_URL}/repositories/{config['workspace']}/"
                f"{config['repo_slug']}/issues"
            )
            params = {"sort": "updated_on", "pagelen": limit}
            if since is not None:
                params["q"] = f'updated_on>="{since.isoformat()}"'

        body = await request_json(
            self._client, "GET", url, params=params, auth=self._auth(credentials)
        )
        values = (body or {}).get("values", [])
        items = [
            ConnectorItem(
                external_id=f"{config['workspace']}/{config['repo_slug']}#{value['id']}",
                title=value["title"],
                kind="issue",
                external_url=value.get("links", {}).get("html", {}).get("href"),
                updated_at=_parse_timestamp(value.get("updated_on")),
                metadata={"content": (value.get("content") or {}).get("raw", "")},
            )
            for value in values
        ]
        return ConnectorPage(items=items, next_cursor=(body or {}).get("next"))

    async def fetch_content(
        self,
        *,
        credentials: ConnectorCredentials,
        config: dict[str, Any],
        item: ConnectorItem,
    ) -> ConnectorContent:
        body = f"# {item.title}\n\n{item.metadata.get('content', '')}"
        return ConnectorContent(
            content=body.encode("utf-8"),
            content_type="text/markdown",
            filename=f"{item.external_id.replace('/', '_')}.md",
        )


def _parse_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
