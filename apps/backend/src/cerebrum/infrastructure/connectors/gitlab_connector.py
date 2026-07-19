"""``GitLabConnector``: a ``Connector`` adapter over the GitLab REST API
(``GET /projects/:id/issues``) — see
https://docs.gitlab.com/ee/api/issues.html#list-project-issues.
Authenticates with a Personal Access Token via the ``PRIVATE-TOKEN``
header. ``config`` keys: ``project_id`` (numeric id or URL-encoded
``namespace/project`` path), optional ``base_url`` (self-hosted
GitLab; defaults to ``https://gitlab.com``).
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

_DEFAULT_BASE_URL = "https://gitlab.com"


class GitLabConnector:
    connector_type = "gitlab"

    def __init__(self, *, http_client: httpx.AsyncClient) -> None:
        self._client = http_client

    @staticmethod
    def _base_url(config: dict[str, Any]) -> str:
        return f"{config.get('base_url', _DEFAULT_BASE_URL).rstrip('/')}/api/v4"

    @staticmethod
    def _headers(credentials: ConnectorCredentials) -> dict[str, str]:
        return {"PRIVATE-TOKEN": credentials.get("token")}

    async def test_connection(
        self, *, credentials: ConnectorCredentials, config: dict[str, Any]
    ) -> bool:
        await request_json(
            self._client,
            "GET",
            f"{self._base_url(config)}/projects/{config['project_id']}",
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
            "order_by": "updated_at",
            "sort": "asc",
            "per_page": limit,
            "page": int(cursor) if cursor else 1,
        }
        if since is not None:
            params["updated_after"] = since.isoformat()

        body = await request_json(
            self._client,
            "GET",
            f"{self._base_url(config)}/projects/{config['project_id']}/issues",
            headers=self._headers(credentials),
            params=params,
        )
        issues = body or []
        items = [
            ConnectorItem(
                external_id=f"{config['project_id']}#{issue['iid']}",
                title=issue["title"],
                kind="issue",
                external_url=issue.get("web_url"),
                updated_at=_parse_timestamp(issue.get("updated_at")),
                metadata={"description": issue.get("description") or ""},
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
        body = f"# {item.title}\n\n{item.metadata.get('description', '')}"
        return ConnectorContent(
            content=body.encode("utf-8"),
            content_type="text/markdown",
            filename=f"{item.external_id.replace('/', '_')}.md",
        )


def _parse_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
