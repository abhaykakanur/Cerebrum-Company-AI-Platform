"""Proves CIS Phase 5 Prompt 3's orchestrator,
``EmployeeKnowledgeCapsuleService``: capsule creation, explicit
human-confirmed identity linking, operator-set profile fields,
``refresh`` (composing real ``ExpertiseInferenceService``/
``OwnershipInferenceService``/``OrganizationalMemoryService`` against
real, SQLite-backed knowledge-graph data — see
test_capsule_repository.py's docstring for why real SQL, not fakes, is
what's tested), Continuous Updates (``ContinuousUpdateListener`` wired
onto a real ``EventDispatcher``), and the read-side endpoints (compare,
search, organizational knowledge map, AI capsule).
"""

import uuid
from typing import Any

import pytest
from _auth_factories import create_organization, create_user, create_workspace
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.auth.audit_service import AuditService
from cerebrum.application.capsules.capsule_graph_service import CapsuleGraphService
from cerebrum.application.capsules.continuous_updates import ContinuousUpdateListener
from cerebrum.application.capsules.employee_knowledge_capsule_service import (
    EmployeeKnowledgeCapsuleService,
)
from cerebrum.application.capsules.events import (
    CapsuleCreatedEvent,
    CapsuleRefreshedEvent,
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
from cerebrum.application.connectors.events import SyncCompletedEvent
from cerebrum.application.knowledge_graph.entity_service import EntityService
from cerebrum.application.knowledge_graph.relationship_service import (
    RelationshipService,
)
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.audit import AuditEvent, AuditEventType
from cerebrum.infrastructure.database.models.entity import EntityType
from cerebrum.infrastructure.database.models.relationship import RelationshipType
from cerebrum.repositories.contracts import Pagination
from cerebrum.repositories.postgres.audit_repository import AuditEventRepository
from cerebrum.repositories.postgres.capsule_evidence_repository import (
    CapsuleEvidenceRepository,
)
from cerebrum.repositories.postgres.capsule_repository import CapsuleRepository
from cerebrum.repositories.postgres.capsule_timeline_repository import (
    CapsuleTimelineRepository,
)
from cerebrum.repositories.postgres.entity_repository import EntityRepository
from cerebrum.repositories.postgres.relationship_repository import (
    RelationshipRepository,
)
from cerebrum.shared.errors.exceptions import NotFoundException, ValidationException

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


class _FakeGraphRepository:
    async def upsert_entity_node(self, **kwargs: Any) -> None:
        pass

    async def upsert_relationship_edge(self, **kwargs: Any) -> None:
        pass


def _service(
    session: AsyncSession, *, events: EventDispatcher | None = None
) -> EmployeeKnowledgeCapsuleService:
    events = events or EventDispatcher()
    audit = AuditService(AuditEventRepository(session))
    entity_service = EntityService(entity_repository=EntityRepository(session))
    relationship_service = RelationshipService(
        relationship_repository=RelationshipRepository(session)
    )
    capsule_graph = CapsuleGraphService(
        entity_service=entity_service,
        relationship_service=relationship_service,
        graph_repository=_FakeGraphRepository(),  # type: ignore[arg-type]
    )
    return EmployeeKnowledgeCapsuleService(
        capsule_repository=CapsuleRepository(session),
        evidence_repository=CapsuleEvidenceRepository(session),
        timeline_repository=CapsuleTimelineRepository(session),
        capsule_graph_service=capsule_graph,
        expertise_service=ExpertiseInferenceService(
            relationship_service=relationship_service, entity_service=entity_service
        ),
        ownership_service=OwnershipInferenceService(
            relationship_service=relationship_service,
            entity_service=entity_service,
            capsule_graph_service=capsule_graph,
        ),
        memory_service=OrganizationalMemoryService(),
        relationship_service=relationship_service,
        entity_service=entity_service,
        event_dispatcher=events,
        audit_service=audit,
    )


async def _last_audit_event(session: AsyncSession) -> AuditEvent:
    from sqlalchemy import select

    result = await session.execute(
        select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(1)
    )
    return result.scalar_one()


async def test_get_or_create_for_user_is_idempotent(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    events = EventDispatcher()
    created: list[CapsuleCreatedEvent] = []
    events.subscribe(CapsuleCreatedEvent, created.append)
    service = _service(db_session, events=events)

    first = await service.get_or_create_for_user(
        user_id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        created_by=user_id,
    )
    await db_session.commit()
    second = await service.get_or_create_for_user(
        user_id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        created_by=user_id,
    )
    await db_session.commit()

    assert first.id == second.id
    assert first.is_stale is True
    assert len(created) == 1
    audit_event = await _last_audit_event(db_session)
    assert audit_event.event_type == AuditEventType.CAPSULE_CREATED.value


async def test_get_raises_not_found_for_wrong_workspace(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    capsule = await service.get_or_create_for_user(
        user_id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        created_by=user_id,
    )
    await db_session.commit()

    with pytest.raises(NotFoundException):
        await service.get(capsule.id, workspace_id=uuid.uuid4())


async def test_link_person_entity_creates_evidence_and_marks_stale(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    entity_service = EntityService(entity_repository=EntityRepository(db_session))
    capsule = await service.get_or_create_for_user(
        user_id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        created_by=user_id,
    )
    person = await entity_service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        entity_type=EntityType.PERSON,
        canonical_name="Alice Example",
        created_by=user_id,
    )
    await db_session.commit()

    linked = await service.link_person_entity(
        capsule.id, person.id, workspace_id=workspace_id, linked_by=user_id
    )
    await db_session.commit()

    assert linked.person_entity_id == person.id
    assert linked.is_stale is True
    evidence = await service.list_evidence(capsule.id, workspace_id=workspace_id)
    assert len(evidence) == 1
    assert evidence[0].insight_type == "identity_link"


async def test_link_person_entity_rejects_non_person(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    entity_service = EntityService(entity_repository=EntityRepository(db_session))
    capsule = await service.get_or_create_for_user(
        user_id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        created_by=user_id,
    )
    tech = await entity_service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        entity_type=EntityType.TECHNOLOGY,
        canonical_name="Kubernetes",
        created_by=user_id,
    )
    await db_session.commit()

    with pytest.raises(ValidationException):
        await service.link_person_entity(
            capsule.id, tech.id, workspace_id=workspace_id, linked_by=user_id
        )


async def test_update_profile_sets_operator_provided_fields(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    capsule = await service.get_or_create_for_user(
        user_id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        created_by=user_id,
    )
    await db_session.commit()

    updated = await service.update_profile(
        capsule.id,
        workspace_id=workspace_id,
        organizational_role="Staff Engineer",
        responsibilities=["Platform reliability"],
        updated_by=user_id,
    )
    await db_session.commit()

    assert updated.organizational_role == "Staff Engineer"
    assert updated.responsibilities == ["Platform reliability"]


async def test_refresh_raises_when_not_linked(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    capsule = await service.get_or_create_for_user(
        user_id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        created_by=user_id,
    )
    await db_session.commit()

    with pytest.raises(ValidationException):
        await service.refresh(
            capsule.id,
            workspace_id=workspace_id,
            organization_id=organization_id,
            triggered_by=user_id,
        )


async def _seed_linked_capsule(  # type: ignore[no-untyped-def]
    db_session: AsyncSession, *, events: EventDispatcher | None = None
):
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session, events=events)
    entity_service = EntityService(entity_repository=EntityRepository(db_session))
    relationship_service = RelationshipService(
        relationship_repository=RelationshipRepository(db_session)
    )
    capsule = await service.get_or_create_for_user(
        user_id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        created_by=user_id,
    )
    person = await entity_service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        entity_type=EntityType.PERSON,
        canonical_name="Alice Example",
        created_by=user_id,
    )
    kubernetes = await entity_service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        entity_type=EntityType.TECHNOLOGY,
        canonical_name="Kubernetes",
        created_by=user_id,
    )
    repo = await entity_service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        entity_type=EntityType.CUSTOM,
        custom_type_name="repository",
        canonical_name="acme/widgets",
        created_by=user_id,
    )
    await db_session.commit()
    for _ in range(4):
        await relationship_service.create(
            workspace_id=workspace_id,
            organization_id=organization_id,
            source_entity_id=person.id,
            target_entity_id=kubernetes.id,
            relationship_type=RelationshipType.MENTIONS,
            confidence=0.7,
            created_by=user_id,
        )
    for _ in range(5):
        await relationship_service.create(
            workspace_id=workspace_id,
            organization_id=organization_id,
            source_entity_id=person.id,
            target_entity_id=repo.id,
            relationship_type=RelationshipType.REFERENCES,
            confidence=0.9,
            created_by=user_id,
        )
    await db_session.commit()
    await service.link_person_entity(
        capsule.id, person.id, workspace_id=workspace_id, linked_by=user_id
    )
    await db_session.commit()
    return service, capsule, workspace_id, organization_id, user_id


async def test_refresh_builds_maps_and_timeline(db_session: AsyncSession) -> None:
    events = EventDispatcher()
    refreshed_events: list[CapsuleRefreshedEvent] = []
    events.subscribe(CapsuleRefreshedEvent, refreshed_events.append)
    service, capsule, workspace_id, organization_id, user_id = (
        await _seed_linked_capsule(db_session, events=events)
    )

    refreshed = await service.refresh(
        capsule.id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        triggered_by=user_id,
    )
    await db_session.commit()

    assert refreshed.is_stale is False
    assert refreshed.last_refreshed_at is not None
    assert len(refreshed.expertise_map) == 1
    assert refreshed.expertise_map[0]["canonical_name"] == "Kubernetes"
    # Both the repo (5 REFERENCES @ 0.9) and Kubernetes (4 MENTIONS @
    # 0.7) cross _MIN_OWNERSHIP_SCORE, so both become ownership
    # candidates — a technology, not only a repository, can be
    # genuinely "owned" given strong enough evidence.
    ownership_by_name = {
        item["canonical_name"]: item for item in refreshed.ownership_map
    }
    assert set(ownership_by_name) == {"acme/widgets", "Kubernetes"}
    assert ownership_by_name["acme/widgets"]["ownership_category"] == "repository"
    assert ownership_by_name["Kubernetes"]["ownership_category"] == "general"
    assert len(refreshed.technical_leadership) == len(refreshed.ownership_map)
    assert len(refreshed_events) == 1

    evidence = await service.list_evidence(capsule.id, workspace_id=workspace_id)
    insight_types = {record.insight_type for record in evidence}
    assert "identity_link" in insight_types
    assert "expertise" in insight_types
    assert "ownership" in insight_types

    timeline_page = await service.list_timeline(
        capsule.id,
        workspace_id=workspace_id,
        pagination=Pagination(page=1, page_size=50),
    )
    assert timeline_page.total_items > 0


async def test_refresh_replaces_evidence_rather_than_accumulating(
    db_session: AsyncSession,
) -> None:
    service, capsule, workspace_id, organization_id, user_id = (
        await _seed_linked_capsule(db_session)
    )

    await service.refresh(
        capsule.id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        triggered_by=user_id,
    )
    await db_session.commit()
    first_pass_evidence = await service.list_evidence(
        capsule.id, workspace_id=workspace_id
    )

    await service.refresh(
        capsule.id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        triggered_by=user_id,
    )
    await db_session.commit()
    second_pass_evidence = await service.list_evidence(
        capsule.id, workspace_id=workspace_id
    )

    assert len(second_pass_evidence) == len(first_pass_evidence)


async def test_mark_stale_and_list_stale(db_session: AsyncSession) -> None:
    service, capsule, workspace_id, organization_id, user_id = (
        await _seed_linked_capsule(db_session)
    )
    await service.refresh(
        capsule.id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        triggered_by=user_id,
    )
    await db_session.commit()

    await service.mark_stale(capsule.id, workspace_id=workspace_id, reason="test")
    await db_session.commit()

    stale = await service.list_stale(workspace_id=workspace_id)
    assert [c.id for c in stale] == [capsule.id]


async def test_mark_stale_for_workspace(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    capsule = await service.get_or_create_for_user(
        user_id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        created_by=user_id,
    )
    await db_session.commit()
    # A freshly-created capsule is already stale by default — force it
    # non-stale first so mark_stale_for_workspace has something to do.
    capsule.is_stale = False
    await db_session.commit()

    marked = await service.mark_stale_for_workspace(
        workspace_id, reason="continuous update"
    )
    await db_session.commit()

    assert marked == 1


async def test_delete_soft_deletes(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    capsule = await service.get_or_create_for_user(
        user_id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        created_by=user_id,
    )
    await db_session.commit()

    await service.delete(capsule.id, workspace_id=workspace_id, deleted_by=user_id)
    await db_session.commit()

    with pytest.raises(NotFoundException):
        await service.get(capsule.id, workspace_id=workspace_id)


async def test_compare_finds_shared_and_unique_expertise(
    db_session: AsyncSession,
) -> None:
    service, capsule, workspace_id, organization_id, user_id = (
        await _seed_linked_capsule(db_session)
    )
    await service.refresh(
        capsule.id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        triggered_by=user_id,
    )
    await db_session.commit()

    other_user_id = uuid.uuid4()
    entity_service = EntityService(entity_repository=EntityRepository(db_session))
    other_person = await entity_service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        entity_type=EntityType.PERSON,
        canonical_name="Bob Example",
        created_by=user_id,
    )
    other_capsule = await service.get_or_create_for_user(
        other_user_id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        created_by=user_id,
    )
    await db_session.commit()
    await service.link_person_entity(
        other_capsule.id, other_person.id, workspace_id=workspace_id, linked_by=user_id
    )
    await db_session.commit()

    capsule_user_id = capsule.user_id
    comparison = await service.compare(
        capsule_user_id, other_user_id, workspace_id=workspace_id
    )

    assert "Kubernetes" in comparison["unique_expertise_a"]
    assert comparison["shared_expertise"] == []


async def test_expertise_and_ownership_search(db_session: AsyncSession) -> None:
    service, capsule, workspace_id, organization_id, user_id = (
        await _seed_linked_capsule(db_session)
    )
    await service.refresh(
        capsule.id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        triggered_by=user_id,
    )
    await db_session.commit()

    expertise_results = await service.expertise_search(
        workspace_id=workspace_id, query="kubernetes"
    )
    assert len(expertise_results) == 1
    assert expertise_results[0]["user_id"] == str(capsule.user_id)

    ownership_results = await service.ownership_search(
        workspace_id=workspace_id, query="widgets"
    )
    assert len(ownership_results) == 1

    assert await service.expertise_search(workspace_id=workspace_id, query="nope") == []


async def test_organizational_knowledge_map(db_session: AsyncSession) -> None:
    service, capsule, workspace_id, organization_id, user_id = (
        await _seed_linked_capsule(db_session)
    )
    await service.refresh(
        capsule.id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        triggered_by=user_id,
    )
    await db_session.commit()

    entries = await service.organizational_knowledge_map(workspace_id=workspace_id)

    assert len(entries) == 1
    assert entries[0]["top_expertise"][0]["canonical_name"] == "Kubernetes"


async def test_get_ai_capsule_returns_structured_payload_only(
    db_session: AsyncSession,
) -> None:
    service, capsule, workspace_id, organization_id, user_id = (
        await _seed_linked_capsule(db_session)
    )
    await service.refresh(
        capsule.id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        triggered_by=user_id,
    )
    await db_session.commit()

    payload = await service.get_ai_capsule(capsule.id, workspace_id=workspace_id)

    assert payload["capsule_id"] == str(capsule.id)
    assert payload["expertise_map"][0]["canonical_name"] == "Kubernetes"
    assert payload["graph_references"]["person_entity_id"] is not None
    assert "retrieval_references" in payload
    assert "dependency_graph" in payload


async def test_continuous_update_listener_integration(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    events = EventDispatcher()
    listener = ContinuousUpdateListener()
    listener.register(events)
    service = _service(db_session, events=events)

    capsule = await service.get_or_create_for_user(
        user_id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        created_by=user_id,
    )
    await db_session.commit()
    capsule.is_stale = False
    await db_session.commit()

    events.publish(
        SyncCompletedEvent(
            connector_id=uuid.uuid4(),
            workspace_id=workspace_id,
            sync_run_id=uuid.uuid4(),
            items_processed=1,
            items_skipped=0,
            items_failed=0,
        )
    )

    pending = listener.drain_pending_workspaces()
    assert pending == [workspace_id]

    marked = await service.mark_stale_for_workspace(
        workspace_id, reason="connector sync"
    )
    await db_session.commit()

    assert marked == 1
    refreshed_capsule = await service.get(capsule.id, workspace_id=workspace_id)
    assert refreshed_capsule.is_stale is True
    assert refreshed_capsule.stale_reason == "connector sync"
