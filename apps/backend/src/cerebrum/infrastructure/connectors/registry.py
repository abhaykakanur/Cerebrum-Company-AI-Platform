"""Connector selection — CIS Phase 5 Prompt 1's Connector Registry.
:func:`build_connector` is the one place that maps a
:class:`~cerebrum.infrastructure.database.models.connector.ConnectorType`
to a concrete :class:`~cerebrum.infrastructure.connectors.base.Connector`
instance; nothing above cerebrum.application.connectors imports a
concrete adapter class directly — mirrors
cerebrum.infrastructure.llm.registry's identical role for LLM providers.
"""

import httpx

from cerebrum.infrastructure.connectors.azure_devops_connector import (
    AzureDevOpsConnector,
)
from cerebrum.infrastructure.connectors.base import Connector
from cerebrum.infrastructure.connectors.bitbucket_connector import BitbucketConnector
from cerebrum.infrastructure.connectors.confluence_connector import (
    ConfluenceConnector,
)
from cerebrum.infrastructure.connectors.github_connector import GitHubConnector
from cerebrum.infrastructure.connectors.gitlab_connector import GitLabConnector
from cerebrum.infrastructure.connectors.jira_connector import JiraConnector
from cerebrum.infrastructure.connectors.notion_connector import NotionConnector
from cerebrum.infrastructure.connectors.slack_connector import SlackConnector
from cerebrum.infrastructure.connectors.teams_connector import TeamsConnector
from cerebrum.infrastructure.database.models.connector import ConnectorType
from cerebrum.shared.errors.exceptions import ValidationException

_ADAPTERS: dict[ConnectorType, type[Connector]] = {
    ConnectorType.GITHUB: GitHubConnector,
    ConnectorType.GITLAB: GitLabConnector,
    ConnectorType.BITBUCKET: BitbucketConnector,
    ConnectorType.JIRA: JiraConnector,
    ConnectorType.AZURE_DEVOPS: AzureDevOpsConnector,
    ConnectorType.CONFLUENCE: ConfluenceConnector,
    ConnectorType.NOTION: NotionConnector,
    ConnectorType.SLACK: SlackConnector,
    ConnectorType.TEAMS: TeamsConnector,
}

SUPPORTED_CONNECTOR_TYPES = tuple(t.value for t in _ADAPTERS)


def build_connector(
    connector_type: ConnectorType, *, http_client: httpx.AsyncClient
) -> Connector:
    adapter_cls = _ADAPTERS.get(connector_type)
    if adapter_cls is None:
        raise ValidationException(
            f"Unknown connector type '{connector_type}'. Supported connector "
            f"types: {', '.join(SUPPORTED_CONNECTOR_TYPES)}."
        )
    return adapter_cls(http_client=http_client)  # type: ignore[call-arg]
