"""FastAPI DI providers for CIS Phase 5 Prompt 2's Enterprise
Automation & Workflow Engine. Mirrors
cerebrum.dependencies.connectors's exact pattern:
``get_workflow_run_service`` composes already-established providers
(``get_connector_sync_service``, ``get_rag_service``,
``get_retrieval_service``, ``get_search_service``) rather than
re-building any of CIS Phase 4/5 Prompt 1's services — the DI-layer
expression of "reuse all existing services... do not duplicate
connector, retrieval, reasoning or AI logic".
"""

from typing import Annotated

from fastapi import Depends

from cerebrum.application.auth.audit_service import AuditService
from cerebrum.application.workflows.scheduler import WorkflowScheduler
from cerebrum.application.workflows.step_executors import (
    AIReasoningStepExecutor,
    ConnectorActionStepExecutor,
    CustomStepExecutor,
    NotificationStepExecutor,
    RetrievalStepExecutor,
    SearchStepExecutor,
    StepExecutor,
)
from cerebrum.application.workflows.workflow_run_service import WorkflowRunService
from cerebrum.application.workflows.workflow_service import WorkflowService
from cerebrum.dependencies.ai import get_rag_service
from cerebrum.dependencies.connectors import (
    get_connector_sync_service,
)
from cerebrum.dependencies.database import DbSessionDep
from cerebrum.dependencies.infrastructure import (
    EventDispatcherDep,
    HttpClientDep,
    MinIODep,
    Neo4jDep,
    OpenSearchDep,
    QdrantDep,
    RedisDep,
)
from cerebrum.dependencies.retrieval import get_retrieval_service
from cerebrum.dependencies.semantic import get_search_service
from cerebrum.dependencies.settings import SettingsDep
from cerebrum.infrastructure.database.models.workflow_version import StepType
from cerebrum.repositories.postgres.audit_repository import AuditEventRepository
from cerebrum.repositories.postgres.workflow_repository import WorkflowRepository
from cerebrum.repositories.postgres.workflow_run_repository import WorkflowRunRepository
from cerebrum.repositories.postgres.workflow_schedule_repository import (
    WorkflowScheduleRepository,
)
from cerebrum.repositories.postgres.workflow_step_run_repository import (
    WorkflowStepRunRepository,
)
from cerebrum.repositories.postgres.workflow_version_repository import (
    WorkflowVersionRepository,
)


def get_workflow_repository(session: DbSessionDep) -> WorkflowRepository:
    return WorkflowRepository(session)


def get_workflow_version_repository(
    session: DbSessionDep,
) -> WorkflowVersionRepository:
    return WorkflowVersionRepository(session)


def get_workflow_run_repository(session: DbSessionDep) -> WorkflowRunRepository:
    return WorkflowRunRepository(session)


def get_workflow_step_run_repository(
    session: DbSessionDep,
) -> WorkflowStepRunRepository:
    return WorkflowStepRunRepository(session)


def get_workflow_schedule_repository(
    session: DbSessionDep,
) -> WorkflowScheduleRepository:
    return WorkflowScheduleRepository(session)


def get_workflow_service(
    session: DbSessionDep, event_dispatcher: EventDispatcherDep
) -> WorkflowService:
    return WorkflowService(
        workflow_repository=get_workflow_repository(session),
        workflow_version_repository=get_workflow_version_repository(session),
        event_dispatcher=event_dispatcher,
        audit_service=AuditService(AuditEventRepository(session)),
    )


def _get_step_executors(
    session: DbSessionDep,
    minio_client: MinIODep,
    neo4j_driver: Neo4jDep,
    qdrant_client: QdrantDep,
    opensearch_client: OpenSearchDep,
    redis: RedisDep,
    http_client: HttpClientDep,
    settings: SettingsDep,
    event_dispatcher: EventDispatcherDep,
) -> dict[StepType, StepExecutor]:
    return {
        StepType.CONNECTOR_ACTION: ConnectorActionStepExecutor(
            connector_sync_service=get_connector_sync_service(
                session,
                minio_client,
                neo4j_driver,
                qdrant_client,
                opensearch_client,
                http_client,
                settings,
                event_dispatcher,
            )
        ),
        StepType.AI_REASONING: AIReasoningStepExecutor(
            rag_service=get_rag_service(
                session,
                qdrant_client,
                opensearch_client,
                neo4j_driver,
                redis,
                event_dispatcher,
            ),
            ai_settings=settings.ai,
            http_client=http_client,
        ),
        StepType.RETRIEVAL: RetrievalStepExecutor(
            retrieval_service=get_retrieval_service(
                session,
                qdrant_client,
                opensearch_client,
                neo4j_driver,
                event_dispatcher,
            )
        ),
        StepType.SEARCH: SearchStepExecutor(
            search_service=get_search_service(
                session, opensearch_client, event_dispatcher
            )
        ),
        StepType.NOTIFICATION: NotificationStepExecutor(),
        StepType.CUSTOM: CustomStepExecutor(),
    }


def get_workflow_run_service(
    session: DbSessionDep,
    minio_client: MinIODep,
    neo4j_driver: Neo4jDep,
    qdrant_client: QdrantDep,
    opensearch_client: OpenSearchDep,
    redis: RedisDep,
    http_client: HttpClientDep,
    settings: SettingsDep,
    event_dispatcher: EventDispatcherDep,
) -> WorkflowRunService:
    return WorkflowRunService(
        workflow_service=get_workflow_service(session, event_dispatcher),
        workflow_version_repository=get_workflow_version_repository(session),
        workflow_run_repository=get_workflow_run_repository(session),
        workflow_step_run_repository=get_workflow_step_run_repository(session),
        step_executors=_get_step_executors(
            session,
            minio_client,
            neo4j_driver,
            qdrant_client,
            opensearch_client,
            redis,
            http_client,
            settings,
            event_dispatcher,
        ),
        event_dispatcher=event_dispatcher,
        audit_service=AuditService(AuditEventRepository(session)),
    )


def get_workflow_scheduler(
    session: DbSessionDep,
    minio_client: MinIODep,
    neo4j_driver: Neo4jDep,
    qdrant_client: QdrantDep,
    opensearch_client: OpenSearchDep,
    redis: RedisDep,
    http_client: HttpClientDep,
    settings: SettingsDep,
    event_dispatcher: EventDispatcherDep,
) -> WorkflowScheduler:
    return WorkflowScheduler(
        schedule_repository=get_workflow_schedule_repository(session),
        run_service=get_workflow_run_service(
            session,
            minio_client,
            neo4j_driver,
            qdrant_client,
            opensearch_client,
            redis,
            http_client,
            settings,
            event_dispatcher,
        ),
        audit_service=AuditService(AuditEventRepository(session)),
    )


WorkflowServiceDep = Annotated[WorkflowService, Depends(get_workflow_service)]
WorkflowRunServiceDep = Annotated[WorkflowRunService, Depends(get_workflow_run_service)]
WorkflowSchedulerDep = Annotated[WorkflowScheduler, Depends(get_workflow_scheduler)]
