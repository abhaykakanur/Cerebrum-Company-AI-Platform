"""``NotionConnector``: a ``Connector`` adapter over the Notion API
(``POST /v1/search`` for changed pages, ``GET /v1/blocks/{id}/children``
for a page's content) — see
https://developers.notion.com/reference/post-search and
.../reference/get-block-children. Authenticates with an integration
token (``Authorization: Bearer``) — CIS Phase 5 Prompt 1's OAuth2
category; Notion's own integration tokens are bearer tokens regardless
of whether the integration is "internal" (a long-lived token, closer in
practice to a Personal Access Token) or a public OAuth2 app, so this
adapter treats both the same way at the HTTP layer. ``config`` keys:
none required (searches the whole workspace the integration is shared
with); optional ``database_id`` narrows to one database.

Notion's search endpoint has no server-side "changed since" filter — it
only sorts by ``last_edited_time``; this adapter filters client-side
against ``since`` and stops paginating once it sees an item older than
``since`` (results arrive newest-first), the same "the source doesn't
support what we need natively, so we approximate it honestly at the
client" precedent
cerebrum.infrastructure.connectors.azure_devops_connector.AzureDevOpsConnector's
docstring already set.
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

_BASE_URL = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"


class NotionConnector:
    connector_type = "notion"

    def __init__(self, *, http_client: httpx.AsyncClient) -> None:
        self._client = http_client

    @staticmethod
    def _headers(credentials: ConnectorCredentials) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {credentials.get('token')}",
            "Notion-Version": _NOTION_VERSION,
        }

    async def test_connection(
        self, *, credentials: ConnectorCredentials, config: dict[str, Any]
    ) -> bool:
        await request_json(
            self._client,
            "GET",
            f"{_BASE_URL}/users/me",
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
        payload: dict[str, Any] = {
            "sort": {"direction": "descending", "timestamp": "last_edited_time"},
            "page_size": limit,
        }
        if cursor:
            payload["start_cursor"] = cursor
        if config.get("database_id"):
            payload["filter"] = {"property": "object", "value": "page"}

        body = await request_json(
            self._client,
            "POST",
            f"{_BASE_URL}/search",
            headers=self._headers(credentials),
            json=payload,
        )
        results = (body or {}).get("results", [])
        items = []
        stop = False
        for page in results:
            updated_at = _parse_timestamp(page.get("last_edited_time"))
            if since is not None and updated_at is not None and updated_at < since:
                stop = True
                break
            items.append(
                ConnectorItem(
                    external_id=page["id"],
                    title=_extract_title(page),
                    kind="page",
                    external_url=page.get("url"),
                    updated_at=updated_at,
                    metadata={},
                )
            )
        has_more = (body or {}).get("has_more", False)
        next_cursor = (body or {}).get("next_cursor") if has_more and not stop else None
        return ConnectorPage(items=items, next_cursor=next_cursor)

    async def fetch_content(
        self,
        *,
        credentials: ConnectorCredentials,
        config: dict[str, Any],
        item: ConnectorItem,
    ) -> ConnectorContent:
        body = await request_json(
            self._client,
            "GET",
            f"{_BASE_URL}/blocks/{item.external_id}/children",
            headers=self._headers(credentials),
            params={"page_size": 100},
        )
        blocks = (body or {}).get("results", [])
        text = "\n\n".join(_extract_block_text(block) for block in blocks)
        content = f"# {item.title}\n\n{text}"
        return ConnectorContent(
            content=content.encode("utf-8"),
            content_type="text/markdown",
            filename=f"{item.external_id}.md",
        )


def _extract_title(page: dict[str, Any]) -> str:
    properties = page.get("properties", {})
    for candidate in ("title", "Name", "Title"):
        prop = properties.get(candidate)
        if prop and prop.get("type") == "title":
            fragments = prop.get("title", [])
            text = "".join(f.get("plain_text", "") for f in fragments)
            if text:
                return text
    return "Untitled"


def _extract_block_text(block: dict[str, Any]) -> str:
    block_type = block.get("type")
    payload = block.get(block_type, {}) if block_type else {}
    fragments = payload.get("rich_text", [])
    return "".join(f.get("plain_text", "") for f in fragments)


def _parse_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
