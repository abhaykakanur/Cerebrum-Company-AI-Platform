"""``GitHubConnector``: a ``Connector`` adapter over the GitHub REST API
(``GET /repos/{owner}/{repo}/issues``, which returns both issues and
pull requests) — see
https://docs.github.com/en/rest/issues/issues#list-repository-issues.
Authenticates with a Personal Access Token. ``config`` keys: ``owner``,
``repo``. GitHub's issues list endpoint already returns each issue's
full ``body``, so :meth:`fetch_content` needs no second HTTP call — it
reads straight from the ``ConnectorItem.metadata`` :meth:`list_changes`
already populated.
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

_BASE_URL = "https://api.github.com"


class GitHubConnector:
    connector_type = "github"

    def __init__(self, *, http_client: httpx.AsyncClient) -> None:
        self._client = http_client

    @staticmethod
    def _headers(credentials: ConnectorCredentials) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {credentials.get('token')}",
            "Accept": "application/vnd.github+json",
        }

    async def test_connection(
        self, *, credentials: ConnectorCredentials, config: dict[str, Any]
    ) -> bool:
        await request_json(
            self._client,
            "GET",
            f"{_BASE_URL}/repos/{config['owner']}/{config['repo']}",
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
        params: dict[str, Any] = {
            "state": "all",
            "sort": "updated",
            "direction": "asc",
            "per_page": limit,
            "page": int(cursor) if cursor else 1,
        }
        if since is not None:
            params["since"] = since.isoformat()

        body = await request_json(
            self._client,
            "GET",
            f"{_BASE_URL}/repos/{config['owner']}/{config['repo']}/issues",
            headers=self._headers(credentials),
            params=params,
        )
        issues = body or []
        items = [
            ConnectorItem(
                external_id=f"{config['owner']}/{config['repo']}#{issue['number']}",
                title=issue["title"],
                kind="pull_request" if "pull_request" in issue else "issue",
                external_url=issue.get("html_url"),
                updated_at=_parse_timestamp(issue.get("updated_at")),
                metadata={"body": issue.get("body") or ""},
            )
            for issue in issues
        ]
        next_cursor = str(params["page"] + 1) if len(issues) == limit else None
        return ConnectorPage(items=items, next_cursor=next_cursor)

    async def fetch_content(
        self,
        *,
        credentials: ConnectorCredentials,
        config: dict[str, Any],
        item: ConnectorItem,
    ) -> ConnectorContent:
        body = f"# {item.title}\n\n{item.metadata.get('body', '')}"
        return ConnectorContent(
            content=body.encode("utf-8"),
            content_type="text/markdown",
            filename=f"{item.external_id.replace('/', '_')}.md",
        )


def _parse_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
