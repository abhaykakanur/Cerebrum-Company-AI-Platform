"""``JiraConnector``: a ``Connector`` adapter over the Jira Cloud REST
API (``GET /rest/api/3/search``, a JQL query) — see
https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-search/.
Authenticates with an Atlassian API token over HTTP Basic auth (email +
token — Atlassian Cloud's standard API Key scheme, shared with
:class:`~cerebrum.infrastructure.connectors.confluence_connector.ConfluenceConnector`).
``config`` keys: ``base_url`` (e.g. ``https://yourcompany.atlassian.net``),
``project_key``.

Jira issue descriptions are Atlassian Document Format (ADF) — a
recursive JSON tree, not plain text/HTML like every other connector in
this package. :func:`_extract_adf_text` is a small, honest walk of that
tree collecting every ``text`` node (headings, paragraphs, list items)
in document order — not a full ADF renderer (no tables/media/mentions
formatting), the same "narrow but real, not a disguised no-op"
precedent cerebrum.application.ai.safety's docstring set for this
codebase's other necessarily-partial text-extraction utilities.
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


class JiraConnector:
    connector_type = "jira"

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
            f"{base_url}/rest/api/3/myself",
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
        jql = f"project = {config['project_key']}"
        if since is not None:
            jql += f' AND updated >= "{since.strftime("%Y-%m-%d %H:%M")}"'
        jql += " ORDER BY updated ASC"

        start_at = int(cursor) if cursor else 0
        body = await request_json(
            self._client,
            "GET",
            f"{base_url}/rest/api/3/search",
            params={
                "jql": jql,
                "startAt": start_at,
                "maxResults": limit,
                "fields": "summary,updated,description",
            },
            auth=self._auth(credentials),
        )
        issues = (body or {}).get("issues", [])
        total = (body or {}).get("total", 0)
        items = [
            ConnectorItem(
                external_id=issue["key"],
                title=issue["fields"]["summary"],
                kind="issue",
                external_url=f"{base_url}/browse/{issue['key']}",
                updated_at=_parse_timestamp(issue["fields"].get("updated")),
                metadata={"description_adf": issue["fields"].get("description")},
            )
            for issue in issues
        ]
        next_start = start_at + len(issues)
        next_cursor = str(next_start) if next_start < total else None
        return ConnectorPage(items=items, next_cursor=next_cursor)

    async def fetch_content(
        self,
        *,
        credentials: ConnectorCredentials,
        config: dict[str, Any],
        item: ConnectorItem,
    ) -> ConnectorContent:
        description = _extract_adf_text(item.metadata.get("description_adf"))
        body = f"# {item.title}\n\n{description}"
        return ConnectorContent(
            content=body.encode("utf-8"),
            content_type="text/plain",
            filename=f"{item.external_id}.txt",
        )


def _extract_adf_text(node: Any) -> str:
    if node is None:
        return ""
    if isinstance(node, dict):
        if node.get("type") == "text":
            return str(node.get("text", ""))
        return "".join(_extract_adf_text(child) for child in node.get("content", []))
    if isinstance(node, list):
        return "\n".join(_extract_adf_text(child) for child in node)
    return ""


def _parse_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)
