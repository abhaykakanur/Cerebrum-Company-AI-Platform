"""Connector Configuration/Credential Validation — CIS Phase 5 Prompt
1's Connector Validation requirement. A pure, framework-level "does
this config/credential shape have what the named connector type's
adapter will need" check, kept separate from
cerebrum.application.connectors.connector_service.ConnectorService so
the required-keys table lives next to the adapters it actually
describes (each entry names exactly the ``config``/``credentials``
keys that connector's ``list_changes``/``fetch_content`` methods read).
"""

from cerebrum.infrastructure.database.models.connector import ConnectorType

REQUIRED_CONFIG_KEYS: dict[ConnectorType, tuple[str, ...]] = {
    ConnectorType.GITHUB: ("owner", "repo"),
    ConnectorType.GITLAB: ("project_id",),
    ConnectorType.BITBUCKET: ("workspace", "repo_slug"),
    ConnectorType.JIRA: ("base_url", "project_key"),
    ConnectorType.AZURE_DEVOPS: ("organization", "project"),
    ConnectorType.CONFLUENCE: ("base_url", "space_key"),
    ConnectorType.NOTION: (),
    ConnectorType.SLACK: ("channel_id",),
    ConnectorType.TEAMS: ("team_id", "channel_id"),
}

REQUIRED_CREDENTIAL_KEYS: dict[ConnectorType, tuple[str, ...]] = {
    ConnectorType.GITHUB: ("token",),
    ConnectorType.GITLAB: ("token",),
    ConnectorType.BITBUCKET: ("username", "app_password"),
    ConnectorType.JIRA: ("email", "api_token"),
    ConnectorType.AZURE_DEVOPS: ("token",),
    ConnectorType.CONFLUENCE: ("email", "api_token"),
    ConnectorType.NOTION: ("token",),
    ConnectorType.SLACK: ("token",),
    ConnectorType.TEAMS: ("token",),
}


def validate_connector_setup(
    *,
    connector_type: ConnectorType,
    config: dict[str, object],
    credentials: dict[str, object],
) -> list[str]:
    """Returns every missing required key (empty list means valid) —
    never raises itself, so a caller can decide whether a partial
    configuration is acceptable (e.g. saved as a draft) or must be
    rejected outright (CIS Phase 5 Prompt 1's Connector Registration).
    """
    errors = []
    for key in REQUIRED_CONFIG_KEYS.get(connector_type, ()):
        if not config.get(key):
            errors.append(f"Missing required config field '{key}'.")
    for key in REQUIRED_CREDENTIAL_KEYS.get(connector_type, ()):
        if not credentials.get(key):
            errors.append(f"Missing required credential field '{key}'.")
    return errors
