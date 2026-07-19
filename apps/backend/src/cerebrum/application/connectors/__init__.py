"""CIS Phase 5 Prompt 1's Enterprise Connectors & Knowledge
Synchronization — a reusable connector framework
(:mod:`cerebrum.infrastructure.connectors`) plus the application-layer
services that register, configure, schedule, and sync connectors
through the *existing* document/knowledge pipeline:

- :class:`~cerebrum.application.connectors.connector_service.ConnectorService`
  owns Connector Configuration/Lifecycle/Health/Validation persistence.
- :class:`~cerebrum.application.connectors.connector_sync_service.ConnectorSyncService`
  is the sync engine — the only place a connector's fetched items reach
  cerebrum.application.knowledge.document_service.DocumentService,
  cerebrum.application.knowledge.upload_service.UploadService, and
  cerebrum.application.knowledge.knowledge_preparation_service.KnowledgePreparationService,
  per this milestone's OBJECTIVE: "Reuse all existing ingestion,
  parsing, indexing, graph and AI services. Do not duplicate processing
  logic."
- :mod:`cerebrum.application.connectors.scheduler` computes which
  connectors are due for Periodic Sync (see that module's docstring for
  why this codebase queries "due" rather than running a timer itself).

No workflow automation, Employee Knowledge Capsule, frontend, or
production deployment — see this milestone's Non-Objectives.
"""
