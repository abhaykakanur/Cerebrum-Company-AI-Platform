"""Enterprise connector adapters — CIS Phase 5 Prompt 1's Connector
Framework. ``base.py`` defines the one interface
(:class:`~cerebrum.infrastructure.connectors.base.Connector`) every
concrete adapter here (GitHub/GitLab/Bitbucket/Jira/Azure DevOps/
Confluence/Notion/Slack/Teams) implements, mirroring
cerebrum.infrastructure.llm's "provider-independent interface, no
application-layer branch on which concrete adapter is active" shape —
see that package's docstring for the identical precedent.

A connector adapter's job ends at producing normalized
:class:`~cerebrum.infrastructure.connectors.base.ConnectorItem`/
:class:`~cerebrum.infrastructure.connectors.base.ConnectorContent`
objects — it never touches PostgreSQL, MinIO, or the knowledge
pipeline itself; see
cerebrum.application.connectors.connector_sync_service.ConnectorSyncService
for where normalized content is handed to the *existing* document
pipeline (Document -> DocumentVersion -> Extraction -> Chunking ->
Knowledge Graph -> Embeddings -> Search), per this milestone's
OBJECTIVE: "Reuse all existing ingestion... Do not duplicate
processing logic."
"""
