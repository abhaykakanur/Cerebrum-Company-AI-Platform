"""``ConfluenceConnector``: a ``Connector`` adapter over the Confluence
Cloud REST API (``GET /wiki/rest/api/content/search``, a CQL query) —
see
https://developer.atlassian.com/cloud/confluence/rest/v1/api-group-content/#api-wiki-rest-api-content-search-get.
Authenticates the same way as
:class:`~cerebrum.infrastructure.connectors.jira_connector.JiraConnector`
— an Atlassian API token over HTTP Basic auth (email + token).
``config`` keys: ``base_url``, ``space_key``.
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


class ConfluenceConnector:
    connector_type = "confluence"

    def __init__(self, *, http_client: httpx.AsyncClient) -> None:
        self._client = http_client

    @staticmethod
    def _auth(credentials: ConnectorCredentials) -> tuple[str, str]:
        return credentials.get("email"), credentials.get("api_token")

    async def test_connection(
        self, *, credentials: ConnectorCredentials, config: dict[str, Any]
    ) -> bool:
        base_url = config["base_url"].rstrip("/")
        await request_json(
            self._client,
            "GET",
            f"{base_url}/wiki/rest/api/space/{config['space_key']}",
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
        base_url = config["base_url"].rstrip("/")
        cql = f"space=\"{config['space_key']}\" and type=page"
        if since is not None:
            cql += f' and lastmodified>="{since.strftime("%Y-%m-%d %H:%M")}"'
        cql += " order by lastmodified asc"

        start = int(cursor) if cursor else 0
        body = await request_json(
            self._client,
            "GET",
            f"{base_url}/wiki/rest/api/content/search",
            params={
                "cql": cql,
                "start": start,
                "limit": limit,
                "expand": "body.storage,version",
            },
            auth=self._auth(credentials),
        )
        results = (body or {}).get("results", [])
        items = [
            ConnectorItem(
                external_id=page["id"],
                title=page["title"],
                kind="page",
                external_url=(f"{base_url}{page.get('_links', {}).get('webui', '')}"),
                updated_at=_parse_timestamp((page.get("version") or {}).get("when")),
                metadata={
                    "body_html": (page.get("body") or {})
                    .get("storage", {})
                    .get("value", "")
                },
            )
            for page in results
        ]
        next_cursor = str(start + len(results)) if len(results) == limit else None
        return ConnectorPage(items=items, next_cursor=next_cursor)

    async def fetch_content(
        self,
        *,
        credentials: ConnectorCredentials,
        config: dict[str, Any],
        item: ConnectorItem,
    ) -> ConnectorContent:
        body = f"<h1>{item.title}</h1>\n{item.metadata.get('body_html', '')}"
        return ConnectorContent(
            content=body.encode("utf-8"),
            content_type="text/html",
            filename=f"{item.external_id}.html",
        )


def _parse_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
