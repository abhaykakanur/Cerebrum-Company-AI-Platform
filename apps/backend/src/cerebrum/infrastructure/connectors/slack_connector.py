"""``SlackConnector``: a ``Connector`` adapter over the Slack Web API
(``GET /conversations.history``) — see
https://api.slack.com/methods/conversations.history. Authenticates
with an OAuth2 bot token (``Authorization: Bearer``). ``config`` keys:
``channel_id``.

Slack's own success signal is ``{"ok": true/false}`` inside a ``200``
response (a request-level auth failure or unreachable endpoint still
returns HTTP 200 with ``"ok": false``) — every method below checks it
explicitly rather than trusting ``httpx``'s ``raise_for_status``, which
would not catch this.
"""

from datetime import UTC, datetime
from typing import Any

import httpx

from cerebrum.infrastructure.connectors._http import request_json
from cerebrum.infrastructure.connectors.base import (
    ConnectorContent,
    ConnectorCredentials,
    ConnectorError,
    ConnectorItem,
    ConnectorPage,
)

_BASE_URL = "https://slack.com/api"


class SlackConnector:
    connector_type = "slack"

    def __init__(self, *, http_client: httpx.AsyncClient) -> None:
        self._client = http_client

    @staticmethod
    def _headers(credentials: ConnectorCredentials) -> dict[str, str]:
        return {"Authorization": f"Bearer {credentials.get('token')}"}

    @staticmethod
    def _require_ok(body: Any, *, method: str) -> dict[str, Any]:
        if not isinstance(body, dict) or not body.get("ok"):
            error = (
                (body or {}).get("error", "unknown_error") if body else "no_response"
            )
            raise ConnectorError(f"Slack {method} failed: {error}")
        return body

    async def test_connection(
        self, *, credentials: ConnectorCredentials, config: dict[str, Any]
    ) -> bool:
        body = await request_json(
            self._client,
            "GET",
            f"{_BASE_URL}/auth.test",
            headers=self._headers(credentials),
        )
        self._require_ok(body, method="auth.test")
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
        params: dict[str, Any] = {"channel": config["channel_id"], "limit": limit}
        if since is not None:
            params["oldest"] = str(since.timestamp())
        if cursor:
            params["cursor"] = cursor

        body = await request_json(
            self._client,
            "GET",
            f"{_BASE_URL}/conversations.history",
            headers=self._headers(credentials),
            params=params,
        )
        body = self._require_ok(body, method="conversations.history")
        messages = body.get("messages", [])
        items = [
            ConnectorItem(
                external_id=f"{config['channel_id']}:{message['ts']}",
                title=(message.get("text") or "")[:80] or "(no text)",
                kind="message",
                external_url=None,
                updated_at=datetime.fromtimestamp(float(message["ts"]), tz=UTC),
                metadata={"text": message.get("text") or ""},
            )
            for message in messages
            if message.get("type") == "message"
        ]
        next_cursor = body.get("response_metadata", {}).get("next_cursor") or None
        return ConnectorPage(items=items, next_cursor=next_cursor)

    async def fetch_content(
        self,
        *,
        credentials: ConnectorCredentials,
        config: dict[str, Any],
        item: ConnectorItem,
    ) -> ConnectorContent:
        content = item.metadata.get("text", "")
        return ConnectorContent(
            content=content.encode("utf-8"),
            content_type="text/plain",
            filename=f"{item.external_id.replace(':', '_')}.txt",
        )
