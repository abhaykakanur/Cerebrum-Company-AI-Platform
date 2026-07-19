"""Shared HTTP request helper for every connector adapter — folds the
"call, raise_for_status, wrap the exception, decode JSON" sequence each
of the nine adapters would otherwise repeat into one place, mirroring
cerebrum.infrastructure.llm._sse's identical "genuinely
provider-independent, not implied by any one adapter's response shape"
rationale.
"""

from typing import Any

import httpx

from cerebrum.infrastructure.connectors.base import ConnectorError


async def request_json(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    json: Any | None = None,
    auth: httpx.Auth | tuple[str, str] | None = None,
) -> Any:
    try:
        response = await client.request(
            method, url, headers=headers, params=params, json=json, auth=auth
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ConnectorError(f"{method} {url} failed: {exc}") from exc
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError as exc:
        raise ConnectorError(f"{method} {url} returned non-JSON content.") from exc
