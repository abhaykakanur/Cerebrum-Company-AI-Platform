"""FastAPI DI providers for CIS Phase 5 Prompt 1's Enterprise
Connectors & Knowledge Synchronization. Mirrors
cerebrum.dependencies.ai's exact pattern: ``get_connector_sync_service``
composes already-established providers (``get_document_service``,
``get_upload_service``, ``get_knowledge_preparation_service``) rather
than re-building CIS Phase 2/3's ingestion/knowledge pipeline services.
"""

from typing import Annotated

from fastapi import Depends

from cerebrum.application.auth.audit_service import AuditService
from cerebrum.application.connectors.connector_service import ConnectorService
from cerebrum.application.connectors.connector_sync_service import ConnectorSyncService
from cerebrum.application.connectors.scheduler import ConnectorScheduler
from cerebrum.dependencies.database import DbSessionDep
from cerebrum.dependencies.infrastructure import (
    EventDispatcherDep,
    HttpClientDep,
    MinIODep,
    Neo4jDep,
    OpenSearchDep,
    QdrantDep,
)
from cerebrum.dependencies.knowledge import (
    get_document_service,
    get_knowledge_preparation_service,
    get_upload_service,
)
from cerebrum.dependencies.settings import SettingsDep
from cerebrum.repositories.postgres.audit_repository import AuditEventRepository
from cerebrum.repositories.postgres.connector_repository import ConnectorRepository
from cerebrum.repositories.postgres.connector_sync_mapping_repository import (
    ConnectorSyncMappingRepository,
)
from cerebrum.repositories.postgres.connector_sync_run_repository import (
    ConnectorSyncRunRepository,
)


def get_connector_repository(session: DbSessionDep) -> ConnectorRepository:
    return ConnectorRepository(session)


def get_connector_sync_run_repository(
    session: DbSessionDep,
) -> ConnectorSyncRunRepository:
    return ConnectorSyncRunRepository(session)


def get_connector_sync_mapping_repository(
    session: DbSessionDep,
) -> ConnectorSyncMappingRepository:
    return ConnectorSyncMappingRepository(session)


def get_connector_service(
    session: DbSessionDep, event_dispatcher: EventDispatcherDep
) -> ConnectorService:
    return ConnectorService(
        connector_repository=get_connector_repository(session),
        event_dispatcher=event_dispatcher,
        audit_service=AuditService(AuditEventRepository(session)),
    )


def get_connector_sync_service(
    session: DbSessionDep,
    minio_client: MinIODep,
    neo4j_driver: Neo4jDep,
    qdrant_client: QdrantDep,
    opensearch_client: OpenSearchDep,
    http_client: HttpClientDep,
    settings: SettingsDep,
    event_dispatcher: EventDispatcherDep,
) -> ConnectorSyncService:
    return ConnectorSyncService(
        connector_service=get_connector_service(session, event_dispatcher),
        sync_run_repository=get_connector_sync_run_repository(session),
        sync_mapping_repository=get_connector_sync_mapping_repository(session),
        document_service=get_document_service(session),
        upload_service=get_upload_service(
            session,
            minio_client,
            settings,
            neo4j_driver,
            qdrant_client,
            opensearch_client,
            event_dispatcher,
        ),
        knowledge_preparation_service=get_knowledge_preparation_service(
            session,
            minio_client,
            neo4j_driver,
            qdrant_client,
            opensearch_client,
            settings,
            event_dispatcher,
        ),
        http_client=http_client,
        event_dispatcher=event_dispatcher,
        audit_service=AuditService(AuditEventRepository(session)),
    )


def get_connector_scheduler(
    session: DbSessionDep,
    minio_client: MinIODep,
    neo4j_driver: Neo4jDep,
    qdrant_client: QdrantDep,
    opensearch_client: OpenSearchDep,
    http_client: HttpClientDep,
    settings: SettingsDep,
    event_dispatcher: EventDispatcherDep,
) -> ConnectorScheduler:
    return ConnectorScheduler(
        connector_repository=get_connector_repository(session),
        sync_service=get_connector_sync_service(
            session,
            minio_client,
            neo4j_driver,
            qdrant_client,
            opensearch_client,
            http_client,
            settings,
            event_dispatcher,
        ),
    )


ConnectorServiceDep = Annotated[ConnectorService, Depends(get_connector_service)]
ConnectorSyncServiceDep = Annotated[
    ConnectorSyncService, Depends(get_connector_sync_service)
]
ConnectorSchedulerDep = Annotated[ConnectorScheduler, Depends(get_connector_scheduler)]
