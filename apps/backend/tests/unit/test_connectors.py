"""Proves CIS Phase 5 Prompt 1's nine ``Connector`` adapters, plus the
registry and validation modules that select and check them.

Every adapter is exercised against a real ``httpx.AsyncClient`` wired
to ``httpx.MockTransport`` — real request construction (URL, headers,
auth, query/body shape) and real response parsing, without any live
network call (real provider endpoints are unreachable in this sandbox)
— the same stronger-than-a-hand-written-fake precedent
test_llm_providers.py's docstring already established for CIS Phase 4
Prompt 1's LLM adapters.
"""

from datetime import UTC, datetime

import httpx
import pytest

from cerebrum.infrastructure.connectors.azure_devops_connector import (
    AzureDevOpsConnector,
)
from cerebrum.infrastructure.connectors.base import (
    ConnectorError,
    ConnectorItem,
    credentials_from_raw,
)
from cerebrum.infrastructure.connectors.bitbucket_connector import BitbucketConnector
from cerebrum.infrastructure.connectors.confluence_connector import (
    ConfluenceConnector,
)
from cerebrum.infrastructure.connectors.github_connector import GitHubConnector
from cerebrum.infrastructure.connectors.gitlab_connector import GitLabConnector
from cerebrum.infrastructure.connectors.jira_connector import JiraConnector
from cerebrum.infrastructure.connectors.notion_connector import NotionConnector
from cerebrum.infrastructure.connectors.registry import (
    SUPPORTED_CONNECTOR_TYPES,
    build_connector,
)
from cerebrum.infrastructure.connectors.slack_connector import SlackConnector
from cerebrum.infrastructure.connectors.teams_connector import TeamsConnector
from cerebrum.infrastructure.connectors.validation import validate_connector_setup
from cerebrum.infrastructure.database.models.connector import (
    ConnectorAuthType,
    ConnectorType,
)
from cerebrum.shared.errors.exceptions import ValidationException

pytestmark = pytest.mark.unit


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _credentials(auth_type: ConnectorAuthType, **raw) -> object:
    return credentials_from_raw(auth_type=auth_type, raw=raw)


# --- GitHub ------------------------------------------------------------


async def test_github_test_connection() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/acme/widgets"
        assert request.headers["Authorization"] == "Bearer gh-token"
        return httpx.Response(200, json={"id": 1})

    connector = GitHubConnector(http_client=_client(handler))
    credentials = _credentials(
        ConnectorAuthType.PERSONAL_ACCESS_TOKEN, token="gh-token"
    )

    assert await connector.test_connection(
        credentials=credentials, config={"owner": "acme", "repo": "widgets"}
    )


async def test_github_list_changes_parses_issues_and_prs() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["since"] == "2026-01-01T00:00:00+00:00"
        return httpx.Response(
            200,
            json=[
                {
                    "number": 42,
                    "title": "Bug report",
                    "html_url": "https://github.com/acme/widgets/issues/42",
                    "updated_at": "2026-01-02T00:00:00Z",
                    "body": "Something is broken.",
                },
                {
                    "number": 43,
                    "title": "Add feature",
                    "html_url": "https://github.com/acme/widgets/pull/43",
                    "updated_at": "2026-01-03T00:00:00Z",
                    "body": "New feature.",
                    "pull_request": {},
                },
            ],
        )

    connector = GitHubConnector(http_client=_client(handler))
    credentials = _credentials(
        ConnectorAuthType.PERSONAL_ACCESS_TOKEN, token="gh-token"
    )

    page = await connector.list_changes(
        credentials=credentials,
        config={"owner": "acme", "repo": "widgets"},
        since=datetime(2026, 1, 1, tzinfo=UTC),
        limit=2,
    )

    assert [item.kind for item in page.items] == ["issue", "pull_request"]
    assert page.items[0].external_id == "acme/widgets#42"
    assert page.next_cursor == "2"


async def test_github_fetch_content_uses_metadata_no_extra_call() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("fetch_content should not make an HTTP call")

    connector = GitHubConnector(http_client=_client(handler))
    item = ConnectorItem(
        external_id="acme/widgets#42",
        title="Bug report",
        kind="issue",
        metadata={"body": "Something is broken."},
    )

    content = await connector.fetch_content(
        credentials=_credentials(ConnectorAuthType.PERSONAL_ACCESS_TOKEN, token="x"),
        config={},
        item=item,
    )

    assert b"Something is broken." in content.content
    assert content.content_type == "text/markdown"


# --- GitLab ------------------------------------------------------------


async def test_gitlab_list_changes_uses_private_token_header() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["PRIVATE-TOKEN"] == "gl-token"
        return httpx.Response(
            200,
            json=[
                {
                    "iid": 7,
                    "title": "Issue title",
                    "web_url": "https://gitlab.com/acme/widgets/-/issues/7",
                    "updated_at": "2026-01-02T00:00:00Z",
                    "description": "Details.",
                }
            ],
        )

    connector = GitLabConnector(http_client=_client(handler))
    credentials = _credentials(
        ConnectorAuthType.PERSONAL_ACCESS_TOKEN, token="gl-token"
    )

    page = await connector.list_changes(
        credentials=credentials, config={"project_id": "123"}, limit=50
    )

    assert page.items[0].external_id == "123#7"
    assert page.next_cursor is None


# --- Bitbucket ------------------------------------------------------------


async def test_bitbucket_list_changes_uses_basic_auth_and_next_url() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"].startswith("Basic ")
        return httpx.Response(
            200,
            json={
                "values": [
                    {
                        "id": 5,
                        "title": "Issue",
                        "links": {"html": {"href": "https://bitbucket.org/x"}},
                        "updated_on": "2026-01-02T00:00:00Z",
                        "content": {"raw": "body text"},
                    }
                ],
                "next": "https://api.bitbucket.org/2.0/next-page",
            },
        )

    connector = BitbucketConnector(http_client=_client(handler))
    credentials = _credentials(
        ConnectorAuthType.PERSONAL_ACCESS_TOKEN, username="bot", app_password="secret"
    )

    page = await connector.list_changes(
        credentials=credentials, config={"workspace": "acme", "repo_slug": "widgets"}
    )

    assert page.items[0].external_id == "acme/widgets#5"
    assert page.next_cursor == "https://api.bitbucket.org/2.0/next-page"


# --- Jira ------------------------------------------------------------


async def test_jira_list_changes_and_adf_extraction() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "myself" not in request.url.path
        assert request.headers["Authorization"].startswith("Basic ")
        return httpx.Response(
            200,
            json={
                "issues": [
                    {
                        "key": "PROJ-1",
                        "fields": {
                            "summary": "Fix bug",
                            "updated": "2026-01-02T00:00:00.000+0000",
                            "description": {
                                "type": "doc",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [
                                            {"type": "text", "text": "Details here."}
                                        ],
                                    }
                                ],
                            },
                        },
                    }
                ],
                "total": 1,
                "startAt": 0,
                "maxResults": 50,
            },
        )

    connector = JiraConnector(http_client=_client(handler))
    credentials = _credentials(
        ConnectorAuthType.API_KEY, email="a@b.com", api_token="token"
    )

    page = await connector.list_changes(
        credentials=credentials,
        config={"base_url": "https://acme.atlassian.net", "project_key": "PROJ"},
    )

    assert page.items[0].external_id == "PROJ-1"
    assert page.next_cursor is None

    content = await connector.fetch_content(
        credentials=credentials, config={}, item=page.items[0]
    )
    assert b"Details here." in content.content


async def test_jira_test_connection() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/rest/api/3/myself"
        return httpx.Response(200, json={"accountId": "1"})

    connector = JiraConnector(http_client=_client(handler))
    credentials = _credentials(
        ConnectorAuthType.API_KEY, email="a@b.com", api_token="token"
    )

    assert await connector.test_connection(
        credentials=credentials,
        config={"base_url": "https://acme.atlassian.net", "project_key": "PROJ"},
    )


# --- Azure DevOps ------------------------------------------------------------


async def test_azure_devops_list_changes_wiql_then_batch() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.method == "POST":
            return httpx.Response(200, json={"workItems": [{"id": 1}, {"id": 2}]})
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "id": 1,
                        "fields": {
                            "System.Title": "Task one",
                            "System.ChangedDate": "2026-01-02T00:00:00Z",
                            "System.Description": "<p>desc</p>",
                        },
                    },
                    {
                        "id": 2,
                        "fields": {
                            "System.Title": "Task two",
                            "System.ChangedDate": "2026-01-03T00:00:00Z",
                            "System.Description": "<p>desc2</p>",
                        },
                    },
                ]
            },
        )

    connector = AzureDevOpsConnector(http_client=_client(handler))
    credentials = _credentials(ConnectorAuthType.PERSONAL_ACCESS_TOKEN, token="pat")

    page = await connector.list_changes(
        credentials=credentials, config={"organization": "acme", "project": "widgets"}
    )

    assert len(page.items) == 2
    assert page.next_cursor is None
    assert len(calls) == 2


async def test_azure_devops_list_changes_empty_when_no_work_items() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"workItems": []})

    connector = AzureDevOpsConnector(http_client=_client(handler))
    credentials = _credentials(ConnectorAuthType.PERSONAL_ACCESS_TOKEN, token="pat")

    page = await connector.list_changes(
        credentials=credentials, config={"organization": "acme", "project": "widgets"}
    )

    assert page.items == []


# --- Confluence ------------------------------------------------------------


async def test_confluence_list_changes_parses_pages() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "999",
                        "title": "Runbook",
                        "_links": {"webui": "/wiki/spaces/ENG/pages/999"},
                        "version": {"when": "2026-01-02T00:00:00.000Z"},
                        "body": {"storage": {"value": "<p>content</p>"}},
                    }
                ]
            },
        )

    connector = ConfluenceConnector(http_client=_client(handler))
    credentials = _credentials(
        ConnectorAuthType.API_KEY, email="a@b.com", api_token="token"
    )

    page = await connector.list_changes(
        credentials=credentials,
        config={"base_url": "https://acme.atlassian.net", "space_key": "ENG"},
    )

    assert page.items[0].external_id == "999"
    assert (
        page.items[0].external_url
        == "https://acme.atlassian.net/wiki/spaces/ENG/pages/999"
    )


# --- Notion ------------------------------------------------------------


async def test_notion_list_changes_stops_at_since() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Notion-Version"]
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "page-new",
                        "url": "https://notion.so/page-new",
                        "last_edited_time": "2026-01-05T00:00:00.000Z",
                        "properties": {
                            "title": {
                                "type": "title",
                                "title": [{"plain_text": "New page"}],
                            }
                        },
                    },
                    {
                        "id": "page-old",
                        "url": "https://notion.so/page-old",
                        "last_edited_time": "2025-01-01T00:00:00.000Z",
                        "properties": {},
                    },
                ],
                "has_more": True,
                "next_cursor": "abc",
            },
        )

    connector = NotionConnector(http_client=_client(handler))
    credentials = _credentials(ConnectorAuthType.OAUTH2, token="notion-token")

    page = await connector.list_changes(
        credentials=credentials,
        config={},
        since=datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert len(page.items) == 1
    assert page.items[0].title == "New page"
    assert page.next_cursor is None


async def test_notion_fetch_content_concatenates_blocks() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "type": "paragraph",
                        "paragraph": {"rich_text": [{"plain_text": "Hello world."}]},
                    }
                ]
            },
        )

    connector = NotionConnector(http_client=_client(handler))
    item = ConnectorItem(external_id="page-1", title="Doc", kind="page")

    content = await connector.fetch_content(
        credentials=_credentials(ConnectorAuthType.OAUTH2, token="x"),
        config={},
        item=item,
    )

    assert b"Hello world." in content.content


# --- Slack ------------------------------------------------------------


async def test_slack_test_connection_checks_ok_field() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True, "user_id": "U1"})

    connector = SlackConnector(http_client=_client(handler))
    credentials = _credentials(ConnectorAuthType.OAUTH2, token="xoxb-token")

    assert await connector.test_connection(credentials=credentials, config={})


async def test_slack_test_connection_raises_on_not_ok() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": False, "error": "invalid_auth"})

    connector = SlackConnector(http_client=_client(handler))
    credentials = _credentials(ConnectorAuthType.OAUTH2, token="bad-token")

    with pytest.raises(ConnectorError):
        await connector.test_connection(credentials=credentials, config={})


async def test_slack_list_changes_parses_messages() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "ok": True,
                "messages": [
                    {"type": "message", "ts": "1700000000.000100", "text": "hi team"}
                ],
                "response_metadata": {"next_cursor": ""},
            },
        )

    connector = SlackConnector(http_client=_client(handler))
    credentials = _credentials(ConnectorAuthType.OAUTH2, token="xoxb-token")

    page = await connector.list_changes(
        credentials=credentials, config={"channel_id": "C123"}
    )

    assert page.items[0].external_id == "C123:1700000000.000100"
    assert page.items[0].metadata["text"] == "hi team"
    assert page.next_cursor is None


# --- Teams ------------------------------------------------------------


async def test_teams_list_changes_strips_html_for_title() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "id": "msg-1",
                        "webUrl": "https://teams.microsoft.com/msg-1",
                        "createdDateTime": "2026-01-02T00:00:00Z",
                        "body": {"content": "<p>Hello <b>team</b></p>"},
                    }
                ]
            },
        )

    connector = TeamsConnector(http_client=_client(handler))
    credentials = _credentials(ConnectorAuthType.OAUTH2, token="graph-token")

    page = await connector.list_changes(
        credentials=credentials, config={"team_id": "T1", "channel_id": "C1"}
    )

    assert page.items[0].title == "Hello team"
    assert page.next_cursor is None


# --- Registry ------------------------------------------------------------


def test_supported_connector_types_covers_all_nine() -> None:
    assert len(SUPPORTED_CONNECTOR_TYPES) == 9


def test_build_connector_returns_matching_adapter() -> None:
    connector = build_connector(
        ConnectorType.GITHUB, http_client=_client(lambda r: httpx.Response(200))
    )
    assert connector.connector_type == "github"


def test_build_connector_raises_for_unknown_type() -> None:
    with pytest.raises(ValidationException):
        build_connector(
            "not-a-type", http_client=_client(lambda r: httpx.Response(200))  # type: ignore[arg-type]
        )


# --- Validation ------------------------------------------------------------


def test_validate_connector_setup_reports_missing_fields() -> None:
    errors = validate_connector_setup(
        connector_type=ConnectorType.GITHUB, config={}, credentials={}
    )
    assert any("owner" in e for e in errors)
    assert any("token" in e for e in errors)


def test_validate_connector_setup_passes_when_complete() -> None:
    errors = validate_connector_setup(
        connector_type=ConnectorType.GITHUB,
        config={"owner": "acme", "repo": "widgets"},
        credentials={"token": "x"},
    )
    assert errors == []


def test_validate_connector_setup_notion_needs_no_config() -> None:
    errors = validate_connector_setup(
        connector_type=ConnectorType.NOTION, config={}, credentials={"token": "x"}
    )
    assert errors == []
