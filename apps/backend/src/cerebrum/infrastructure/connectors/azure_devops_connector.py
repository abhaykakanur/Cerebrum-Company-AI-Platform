"""``AzureDevOpsConnector``: a ``Connector`` adapter over the Azure
DevOps Work Item Tracking REST API — a WIQL query
(``POST /_apis/wit/wiql``) to find changed work item ids, then a batch
fetch (``GET /_apis/wit/workitems``) for their fields. See
https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/wiql and
.../work-items/list. Authenticates with a Personal Access Token over
HTTP Basic auth (empty username, PAT as password — Azure DevOps's PAT
convention). ``config`` keys: ``organization``, ``project``.

Single-page per sync run (``next_cursor`` is always ``None``): WIQL
does not offer the same page-token pagination GitHub/GitLab/Bitbucket
do, and Azure DevOps work item batches are typically small enough that
this is an honest, documented simplification rather than a silently
incomplete implementation — a workspace with more than ``limit``
changed work items between syncs will pick up the remainder on the next
sync run (the same "eventually consistent under a stable
``sync_interval_seconds``" behavior CIS Phase 5 Prompt 1's Incremental
Synchronization already relies on).
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

_API_VERSION = "7.1"


class AzureDevOpsConnector:
    connector_type = "azure_devops"

    def __init__(self, *, http_client: httpx.AsyncClient) -> None:
        self._client = http_client

    @staticmethod
    def _base_url(config: dict[str, Any]) -> str:
        return (
            f"https://dev.azure.com/{config['organization']}/"
            f"{config['project']}/_apis"
        )

    @staticmethod
    def _auth(credentials: ConnectorCredentials) -> tuple[str, str]:
        return "", credentials.get("token")

    async def test_connection(
        self, *, credentials: ConnectorCredentials, config: dict[str, Any]
    ) -> bool:
        await request_json(
            self._client,
            "GET",
            f"{self._base_url(config)}/wit/workitemtypes",
            params={"api-version": _API_VERSION},
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
        query = "SELECT [System.Id] FROM WorkItems"
        if since is not None:
            query += (
                f" WHERE [System.ChangedDate] >= "
                f"'{since.strftime('%Y-%m-%dT%H:%M:%SZ')}'"
            )
        query += " ORDER BY [System.ChangedDate] ASC"

        wiql = await request_json(
            self._client,
            "POST",
            f"{self._base_url(config)}/wit/wiql",
            params={"api-version": _API_VERSION},
            json={"query": query},
            auth=self._auth(credentials),
        )
        ids = [str(wi["id"]) for wi in (wiql or {}).get("workItems", [])][:limit]
        if not ids:
            return ConnectorPage(items=[], next_cursor=None)

        batch = await request_json(
            self._client,
            "GET",
            f"{self._base_url(config)}/wit/workitems",
            params={
                "ids": ",".join(ids),
                "api-version": _API_VERSION,
                "$expand": "fields",
            },
            auth=self._auth(credentials),
        )
        work_items = (batch or {}).get("value", [])
        items = [
            ConnectorItem(
                external_id=str(work_item["id"]),
                title=work_item["fields"].get("System.Title", ""),
                kind="work_item",
                external_url=(
                    f"https://dev.azure.com/{config['organization']}/"
                    f"{config['project']}/_workitems/edit/{work_item['id']}"
                ),
                updated_at=_parse_timestamp(
                    work_item["fields"].get("System.ChangedDate")
                ),
                metadata={
                    "description": work_item["fields"].get("System.Description", "")
                },
            )
            for work_item in work_items
        ]
        return ConnectorPage(items=items, next_cursor=None)

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
            content_type="text/html",
            filename=f"{item.external_id}.html",
        )


def _parse_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
