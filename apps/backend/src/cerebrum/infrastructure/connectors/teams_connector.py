"""``TeamsConnector``: a ``Connector`` adapter over the Microsoft Graph
API (``GET /teams/{team-id}/channels/{channel-id}/messages``) — see
https://learn.microsoft.com/en-us/graph/api/channel-list-messages.
Authenticates with an Azure AD OAuth2 access token
(``Authorization: Bearer``). ``config`` keys: ``team_id``,
``channel_id``.

Graph list responses page via a full ``@odata.nextLink`` URL (like
:class:`~cerebrum.infrastructure.connectors.bitbucket_connector.BitbucketConnector`'s
``next``) — stored directly as ``next_cursor`` and called as-is on the
following page, no query-parameter reconstruction needed.
"""

import re
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

_BASE_URL = "https://graph.microsoft.com/v1.0"


class TeamsConnector:
    connector_type = "teams"

    def __init__(self, *, http_client: httpx.AsyncClient) -> None:
        self._client = http_client

    @staticmethod
    def _headers(credentials: ConnectorCredentials) -> dict[str, str]:
        return {"Authorization": f"Bearer {credentials.get('token')}"}

    async def test_connection(
        self, *, credentials: ConnectorCredentials, config: dict[str, Any]
    ) -> bool:
        await request_json(
            self._client,
            "GET",
            f"{_BASE_URL}/teams/{config['team_id']}/channels/{config['channel_id']}",
            headers=self._headers(credentials),
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
                f"{_BASE_URL}/teams/{config['team_id']}/channels/"
                f"{config['channel_id']}/messages"
            )
            params = {"$top": limit}

        body = await request_json(
            self._client, "GET", url, headers=self._headers(credentials), params=params
        )
        messages = (body or {}).get("value", [])
        items = []
        for message in messages:
            updated_at = _parse_timestamp(
                message.get("lastModifiedDateTime") or message.get("createdDateTime")
            )
            if since is not None and updated_at is not None and updated_at < since:
                continue
            content_html = (message.get("body") or {}).get("content", "")
            items.append(
                ConnectorItem(
                    external_id=message["id"],
                    title=_strip_html(content_html)[:80] or "(no content)",
                    kind="message",
                    external_url=message.get("webUrl"),
                    updated_at=updated_at,
                    metadata={"content_html": content_html},
                )
            )
        next_cursor = (body or {}).get("@odata.nextLink")
        return ConnectorPage(items=items, next_cursor=next_cursor)

    async def fetch_content(
        self,
        *,
        credentials: ConnectorCredentials,
        config: dict[str, Any],
        item: ConnectorItem,
    ) -> ConnectorContent:
        content = item.metadata.get("content_html", "")
        return ConnectorContent(
            content=content.encode("utf-8"),
            content_type="text/html",
            filename=f"{item.external_id}.html",
        )


def _strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value).strip()


def _parse_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
