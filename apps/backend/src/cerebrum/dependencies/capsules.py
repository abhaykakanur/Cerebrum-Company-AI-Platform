"""FastAPI DI providers for CIS Phase 5 Prompt 3's Employee Knowledge
Capsule. Mirrors cerebrum.dependencies.workflows's exact pattern: each
provider composes already-established providers
(``get_entity_service``, ``get_relationship_service``) rather than
re-building CIS Phase 3's knowledge-graph services.
"""

from typing import Annotated

from fastapi import Depends

from cerebrum.application.auth.audit_service import AuditService
from cerebrum.application.capsules.capsule_graph_service import CapsuleGraphService
from cerebrum.application.capsules.employee_knowledge_capsule_service import (
    EmployeeKnowledgeCapsuleService,
)
from cerebrum.application.capsules.expertise_inference_service import (
    ExpertiseInferenceService,
)
from cerebrum.application.capsules.organizational_memory_service import (
    OrganizationalMemoryService,
)
from cerebrum.application.capsules.ownership_inference_service import (
    OwnershipInferenceService,
)
from cerebrum.application.capsules.risk_analysis_service import RiskAnalysisService
from cerebrum.application.capsules.successor_planning_service import (
    SuccessorPlanningService,
)
from cerebrum.dependencies.database import DbSessionDep
from cerebrum.dependencies.infrastructure import EventDispatcherDep, Neo4jDep
from cerebrum.dependencies.knowledge_graph import (
    get_entity_service,
    get_relationship_service,
)
from cerebrum.repositories.neo4j.knowledge_graph_repository import (
    KnowledgeGraphRepository,
)
from cerebrum.repositories.postgres.audit_repository import AuditEventRepository
from cerebrum.repositories.postgres.capsule_evidence_repository import (
    CapsuleEvidenceRepository,
)
from cerebrum.repositories.postgres.capsule_repository import CapsuleRepository
from cerebrum.repositories.postgres.capsule_timeline_repository import (
    CapsuleTimelineRepository,
)


def get_capsule_repository(session: DbSessionDep) -> CapsuleRepository:
    return CapsuleRepository(session)


def get_capsule_evidence_repository(
    session: DbSessionDep,
) -> CapsuleEvidenceRepository:
    return CapsuleEvidenceRepository(session)


def get_capsule_timeline_repository(
    session: DbSessionDep,
) -> CapsuleTimelineRepository:
    return CapsuleTimelineRepository(session)


def get_capsule_graph_service(
    session: DbSessionDep, neo4j_driver: Neo4jDep
) -> CapsuleGraphService:
    return CapsuleGraphService(
        entity_service=get_entity_service(session),
        relationship_service=get_relationship_service(session),
        graph_repository=KnowledgeGraphRepository(neo4j_driver),
    )


def get_expertise_inference_service(session: DbSessionDep) -> ExpertiseInferenceService:
    return ExpertiseInferenceService(
        relationship_service=get_relationship_service(session),
        entity_service=get_entity_service(session),
    )


def get_ownership_inference_service(
    session: DbSessionDep, neo4j_driver: Neo4jDep
) -> OwnershipInferenceService:
    return OwnershipInferenceService(
        relationship_service=get_relationship_service(session),
        entity_service=get_entity_service(session),
        capsule_graph_service=get_capsule_graph_service(session, neo4j_driver),
    )


def get_organizational_memory_service() -> OrganizationalMemoryService:
    return OrganizationalMemoryService()


def get_risk_analysis_service(session: DbSessionDep) -> RiskAnalysisService:
    return RiskAnalysisService(
        relationship_service=get_relationship_service(session),
        entity_service=get_entity_service(session),
    )


def get_successor_planning_service() -> SuccessorPlanningService:
    return SuccessorPlanningService()


def get_employee_knowledge_capsule_service(
    session: DbSessionDep,
    neo4j_driver: Neo4jDep,
    event_dispatcher: EventDispatcherDep,
) -> EmployeeKnowledgeCapsuleService:
    return EmployeeKnowledgeCapsuleService(
        capsule_repository=get_capsule_repository(session),
        evidence_repository=get_capsule_evidence_repository(session),
        timeline_repository=get_capsule_timeline_repository(session),
        capsule_graph_service=get_capsule_graph_service(session, neo4j_driver),
        expertise_service=get_expertise_inference_service(session),
        ownership_service=get_ownership_inference_service(session, neo4j_driver),
        memory_service=get_organizational_memory_service(),
        relationship_service=get_relationship_service(session),
        entity_service=get_entity_service(session),
        event_dispatcher=event_dispatcher,
        audit_service=AuditService(AuditEventRepository(session)),
    )


CapsuleGraphServiceDep = Annotated[
    CapsuleGraphService, Depends(get_capsule_graph_service)
]
ExpertiseInferenceServiceDep = Annotated[
    ExpertiseInferenceService, Depends(get_expertise_inference_service)
]
OwnershipInferenceServiceDep = Annotated[
    OwnershipInferenceService, Depends(get_ownership_inference_service)
]
RiskAnalysisServiceDep = Annotated[
    RiskAnalysisService, Depends(get_risk_analysis_service)
]
SuccessorPlanningServiceDep = Annotated[
    SuccessorPlanningService, Depends(get_successor_planning_service)
]
EmployeeKnowledgeCapsuleServiceDep = Annotated[
    EmployeeKnowledgeCapsuleService, Depends(get_employee_knowledge_capsule_service)
]
