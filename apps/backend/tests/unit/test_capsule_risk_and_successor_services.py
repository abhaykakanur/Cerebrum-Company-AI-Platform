"""Proves CIS Phase 5 Prompt 3's Risk Analysis
(``RiskAnalysisService`` — Bus Factor, Knowledge Concentration,
Single-Owner Detection, Critical Dependency Detection, Coverage
Scoring, Successor Readiness) and Successor Assistant
(``SuccessorPlanningService``). Risk analysis is exercised against a
real, SQLite-backed ``EntityService``/``RelationshipService`` (see
test_capsule_repository.py's docstring for why); successor planning is
pure computation over in-memory ORM instances, needing no database at
all — mirrors test_organizational_memory_service.py's identical
reasoning.
"""

import uuid

import pytest
from _auth_factories import create_organization, create_user, create_workspace
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.capsules.risk_analysis_service import RiskAnalysisService
from cerebrum.application.capsules.successor_planning_service import (
    SuccessorPlanningService,
)
from cerebrum.application.knowledge_graph.entity_service import EntityService
from cerebrum.application.knowledge_graph.relationship_service import (
    RelationshipService,
)
from cerebrum.infrastructure.database.models.capsule import EmployeeKnowledgeCapsule
from cerebrum.infrastructure.database.models.capsule_evidence import (
    CapsuleEvidenceRecord,
)
from cerebrum.infrastructure.database.models.capsule_timeline_event import (
    CapsuleTimelineEvent,
)
from cerebrum.infrastructure.database.models.entity import EntityType
from cerebrum.infrastructure.database.models.relationship import RelationshipType
from cerebrum.repositories.postgres.entity_repository import EntityRepository
from cerebrum.repositories.postgres.relationship_repository import (
    RelationshipRepository,
)
from cerebrum.utils.clock import utcnow

pytestmark = pytest.mark.unit


def _hasher():  # type: ignore[no-untyped-def]
    from cerebrum.config.security import SecuritySettings
    from cerebrum.infrastructure.security.password import PasswordHasher

    return PasswordHasher(SecuritySettings())


async def _tenant(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    unique = uuid.uuid4().hex[:8]
    org = await create_organization(session, slug=f"acme-{unique}")
    workspace = await create_workspace(session, organization_id=org.id)
    user = await create_user(
        session,
        organization_id=org.id,
        email=f"alice-{unique}@acme.example",
        password="CorrectHorse123!",
        hasher=_hasher(),
    )
    await session.commit()
    return org.id, workspace.id, user.id


def _services(
    session: AsyncSession,
) -> tuple[EntityService, RelationshipService, RiskAnalysisService]:
    entity_service = EntityService(entity_repository=EntityRepository(session))
    relationship_service = RelationshipService(
        relationship_repository=RelationshipRepository(session)
    )
    risk_service = RiskAnalysisService(
        relationship_service=relationship_service, entity_service=entity_service
    )
    return entity_service, relationship_service, risk_service


async def _person(entity_service, *, workspace_id, organization_id, name, created_by):  # type: ignore[no-untyped-def]
    return await entity_service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        entity_type=EntityType.PERSON,
        canonical_name=name,
        created_by=created_by,
    )


async def _repo(entity_service, *, workspace_id, organization_id, name, created_by):  # type: ignore[no-untyped-def]
    return await entity_service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        entity_type=EntityType.CUSTOM,
        custom_type_name="repository",
        canonical_name=name,
        created_by=created_by,
    )


async def test_bus_factor_single_owner_is_high_risk(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    entity_service, relationship_service, risk_service = _services(db_session)
    alice = await _person(
        entity_service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="Alice",
        created_by=user_id,
    )
    repo = await _repo(
        entity_service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="acme/widgets",
        created_by=user_id,
    )
    await relationship_service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        source_entity_id=alice.id,
        target_entity_id=repo.id,
        relationship_type=RelationshipType.OWNERSHIP,
        confidence=1.0,
        created_by=user_id,
    )
    await db_session.commit()

    result = await risk_service.bus_factor(repo.id, workspace_id=workspace_id)

    assert result.bus_factor == 1
    assert result.risk_level == "high"
    assert result.owners[0].canonical_name == "Alice"
    assert result.owners[0].share == 1.0


async def test_bus_factor_no_owners_is_critical(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    entity_service, _, risk_service = _services(db_session)
    repo = await _repo(
        entity_service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="acme/widgets",
        created_by=user_id,
    )
    await db_session.commit()

    result = await risk_service.bus_factor(repo.id, workspace_id=workspace_id)

    assert result.bus_factor == 0
    assert result.risk_level == "critical"
    assert result.owners == []


async def test_bus_factor_split_ownership_needs_two_people(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    entity_service, relationship_service, risk_service = _services(db_session)
    alice = await _person(
        entity_service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="Alice",
        created_by=user_id,
    )
    bob = await _person(
        entity_service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="Bob",
        created_by=user_id,
    )
    carol = await _person(
        entity_service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="Carol",
        created_by=user_id,
    )
    repo = await _repo(
        entity_service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="acme/widgets",
        created_by=user_id,
    )
    for owner, confidence in ((alice, 0.4), (bob, 0.35), (carol, 0.25)):
        await relationship_service.create(
            workspace_id=workspace_id,
            organization_id=organization_id,
            source_entity_id=owner.id,
            target_entity_id=repo.id,
            relationship_type=RelationshipType.OWNERSHIP,
            confidence=confidence,
            created_by=user_id,
        )
    await db_session.commit()

    result = await risk_service.bus_factor(repo.id, workspace_id=workspace_id)

    assert result.bus_factor == 2
    assert result.risk_level == "medium"


async def test_coverage_report_and_single_owner_detection(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    entity_service, relationship_service, risk_service = _services(db_session)
    alice = await _person(
        entity_service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="Alice",
        created_by=user_id,
    )
    covered_repo = await _repo(
        entity_service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="acme/covered",
        created_by=user_id,
    )
    await _repo(
        entity_service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="acme/uncovered",
        created_by=user_id,
    )
    await relationship_service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        source_entity_id=alice.id,
        target_entity_id=covered_repo.id,
        relationship_type=RelationshipType.OWNERSHIP,
        confidence=1.0,
        created_by=user_id,
    )
    await db_session.commit()

    report = await risk_service.coverage_report(workspace_id=workspace_id)

    assert report.total_owned_entities == 2
    assert report.covered_entities == 1
    assert report.coverage_score == 0.5
    assert [r.canonical_name for r in report.single_owner_entities] == ["acme/covered"]


async def test_critical_dependencies_requires_multiple_dependents(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    entity_service, relationship_service, risk_service = _services(db_session)
    alice = await _person(
        entity_service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="Alice",
        created_by=user_id,
    )
    critical_repo = await _repo(
        entity_service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="acme/core",
        created_by=user_id,
    )
    dependent_a = await _repo(
        entity_service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="acme/app-a",
        created_by=user_id,
    )
    dependent_b = await _repo(
        entity_service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="acme/app-b",
        created_by=user_id,
    )
    await relationship_service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        source_entity_id=alice.id,
        target_entity_id=critical_repo.id,
        relationship_type=RelationshipType.OWNERSHIP,
        confidence=1.0,
        created_by=user_id,
    )
    for dependent in (dependent_a, dependent_b):
        await relationship_service.create(
            workspace_id=workspace_id,
            organization_id=organization_id,
            source_entity_id=dependent.id,
            target_entity_id=critical_repo.id,
            relationship_type=RelationshipType.DEPENDENCY,
            confidence=1.0,
            created_by=user_id,
        )
    await db_session.commit()

    critical = await risk_service.critical_dependencies(workspace_id=workspace_id)

    assert [r.canonical_name for r in critical] == ["acme/core"]


async def test_successor_readiness(db_session: AsyncSession) -> None:
    # With exactly two owners, shares always normalize to sum to 1.0, so
    # the top owner's share alone is always >= 0.5 (bus factor 1) —
    # three owners, none individually reaching half, is what actually
    # demonstrates a bus factor of 2 (see
    # test_bus_factor_split_ownership_needs_two_people for the same
    # shares' bus_factor directly).
    organization_id, workspace_id, user_id = await _tenant(db_session)
    entity_service, relationship_service, risk_service = _services(db_session)
    alice = await _person(
        entity_service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="Alice",
        created_by=user_id,
    )
    bob = await _person(
        entity_service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="Bob",
        created_by=user_id,
    )
    carol = await _person(
        entity_service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="Carol",
        created_by=user_id,
    )
    repo = await _repo(
        entity_service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="acme/widgets",
        created_by=user_id,
    )
    for owner, confidence in ((alice, 0.4), (bob, 0.35), (carol, 0.25)):
        await relationship_service.create(
            workspace_id=workspace_id,
            organization_id=organization_id,
            source_entity_id=owner.id,
            target_entity_id=repo.id,
            relationship_type=RelationshipType.OWNERSHIP,
            confidence=confidence,
            created_by=user_id,
        )
    await db_session.commit()

    assert (
        await risk_service.successor_readiness(repo.id, workspace_id=workspace_id)
        is True
    )

    single_owner_repo = await _repo(
        entity_service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="acme/solo",
        created_by=user_id,
    )
    await relationship_service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        source_entity_id=alice.id,
        target_entity_id=single_owner_repo.id,
        relationship_type=RelationshipType.OWNERSHIP,
        confidence=1.0,
        created_by=user_id,
    )
    await db_session.commit()

    assert (
        await risk_service.successor_readiness(
            single_owner_repo.id, workspace_id=workspace_id
        )
        is False
    )


# --- SuccessorPlanningService -------------------------------------------------


def test_generate_plan_ranks_by_score_and_dereferences_evidence() -> None:
    capsule = EmployeeKnowledgeCapsule(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        ownership_map=[
            {
                "entity_id": str(uuid.uuid4()),
                "canonical_name": "acme/core",
                "entity_type": "custom",
                "ownership_category": "repository",
                "share": 1.0,
                "score": 0.9,
                "evidence_count": 2,
            },
            {
                "entity_id": str(uuid.uuid4()),
                "canonical_name": "acme/tooling",
                "entity_type": "custom",
                "ownership_category": "general",
                "share": 1.0,
                "score": 0.4,
                "evidence_count": 1,
            },
        ],
        collaboration_network=[
            {
                "entity_id": str(uuid.uuid4()),
                "canonical_name": "Bob",
                "strength": 0.8,
                "evidence_count": 1,
            }
        ],
    )
    evidence_records = [
        CapsuleEvidenceRecord(
            capsule_id=capsule.id,
            insight_type="ownership",
            insight_key="acme/core",
            confidence=0.9,
            description="Co-occurred often.",
            document_id=uuid.uuid4(),
        ),
        CapsuleEvidenceRecord(
            capsule_id=capsule.id,
            insight_type="identity_link",
            insight_key="Alice",
            confidence=1.0,
            description="Linked by operator.",
        ),
    ]
    timeline = [
        CapsuleTimelineEvent(
            capsule_id=capsule.id,
            event_type="ownership_change",
            occurred_at=utcnow(),
            title="Ownership signal: acme/core",
        )
    ]

    service = SuccessorPlanningService()
    plan = service.generate_plan(
        capsule, evidence_records=evidence_records, recent_timeline=timeline
    )

    assert plan.critical_repositories[0]["canonical_name"] == "acme/core"
    assert plan.learning_sequence[0]["canonical_name"] == "acme/core"
    assert plan.key_collaborators[0]["canonical_name"] == "Bob"
    assert len(plan.recommended_reading) == 1
    assert plan.recommended_reading[0]["insight_key"] == "acme/core"
    assert len(plan.open_work) == 1
    assert "acme/core" in plan.immediate_priorities[0]


def test_generate_plan_handles_empty_capsule() -> None:
    capsule = EmployeeKnowledgeCapsule(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        ownership_map=[],
        collaboration_network=[],
    )

    service = SuccessorPlanningService()
    plan = service.generate_plan(capsule, evidence_records=[], recent_timeline=[])

    assert plan.critical_repositories == []
    assert plan.key_collaborators == []
    assert plan.learning_sequence == []
    assert plan.recommended_reading == []
    assert plan.open_work == []
    assert plan.immediate_priorities == []
