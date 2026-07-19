"""Proves CIS Phase 5 Prompt 3's Knowledge Graph Integration and
Inference Engine:
``CapsuleGraphService`` (person-entity creation, ownership-edge upsert,
Neo4j mirroring via a fake ``KnowledgeGraphRepository``),
``ExpertiseInferenceService`` (Subject Matter Expertise from real
co-occurrence ``Relationship`` rows), and ``OwnershipInferenceService``
(Repository/Service/API/Database/Architectural Ownership, including the
"every insight has evidence" and "score crosses a threshold before an
OWNERSHIP edge is actually written" guarantees) — against a real,
SQLite-backed ``EntityService``/``RelationshipService`` (see
test_capsule_repository.py's docstring for why real SQL, not a
reimplementation of it, is what's tested here).
"""

import uuid
from typing import Any

import pytest
from _auth_factories import create_organization, create_user, create_workspace
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.capsules.capsule_graph_service import CapsuleGraphService
from cerebrum.application.capsules.expertise_inference_service import (
    ExpertiseInferenceService,
)
from cerebrum.application.capsules.ownership_inference_service import (
    OwnershipInferenceService,
)
from cerebrum.application.knowledge_graph.entity_service import EntityService
from cerebrum.application.knowledge_graph.relationship_service import (
    RelationshipService,
)
from cerebrum.infrastructure.database.models.entity import EntityType
from cerebrum.infrastructure.database.models.relationship import RelationshipType
from cerebrum.repositories.postgres.entity_repository import EntityRepository
from cerebrum.repositories.postgres.relationship_repository import (
    RelationshipRepository,
)
from cerebrum.shared.errors.exceptions import ValidationException

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
    def __init__(self) -> None:
        self.entity_upserts: list[dict[str, Any]] = []
        self.relationship_upserts: list[dict[str, Any]] = []

    async def upsert_entity_node(self, **kwargs: Any) -> None:
        self.entity_upserts.append(kwargs)

    async def upsert_relationship_edge(self, **kwargs: Any) -> None:
        self.relationship_upserts.append(kwargs)


def _services(
    session: AsyncSession,
) -> tuple[
    EntityService, RelationshipService, CapsuleGraphService, _FakeGraphRepository
]:
    entity_service = EntityService(entity_repository=EntityRepository(session))
    relationship_service = RelationshipService(
        relationship_repository=RelationshipRepository(session)
    )
    fake_graph = _FakeGraphRepository()
    capsule_graph = CapsuleGraphService(
        entity_service=entity_service,
        relationship_service=relationship_service,
        graph_repository=fake_graph,  # type: ignore[arg-type]
    )
    return entity_service, relationship_service, capsule_graph, fake_graph


# --- CapsuleGraphService ----------------------------------------------------


async def test_create_person_entity_creates_and_mirrors(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    _, _, capsule_graph, fake_graph = _services(db_session)

    entity = await capsule_graph.create_person_entity(
        workspace_id=workspace_id,
        organization_id=organization_id,
        canonical_name="Alice Example",
        created_by=user_id,
    )
    await db_session.commit()

    assert entity.entity_type == EntityType.PERSON.value
    assert len(fake_graph.entity_upserts) == 1
    assert fake_graph.entity_upserts[0]["entity_id"] == entity.id


async def test_get_person_entity_rejects_non_person(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    entity_service, _, capsule_graph, _ = _services(db_session)
    tech = await entity_service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        entity_type=EntityType.TECHNOLOGY,
        canonical_name="Kubernetes",
        created_by=user_id,
    )
    await db_session.commit()

    with pytest.raises(ValidationException):
        await capsule_graph.get_person_entity(tech.id, workspace_id=workspace_id)


async def test_upsert_edge_creates_and_strengthens(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    entity_service, _, capsule_graph, fake_graph = _services(db_session)
    person = await entity_service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        entity_type=EntityType.PERSON,
        canonical_name="Alice Example",
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

    first = await capsule_graph.upsert_edge(
        source_entity_id=person.id,
        target_entity_id=repo.id,
        relationship_type=RelationshipType.OWNERSHIP,
        workspace_id=workspace_id,
        organization_id=organization_id,
        confidence=0.4,
        evidence_text="Initial co-occurrence.",
        created_by=user_id,
    )
    await db_session.commit()
    assert first.confidence == 0.4
    assert len(fake_graph.relationship_upserts) == 1

    second = await capsule_graph.upsert_edge(
        source_entity_id=person.id,
        target_entity_id=repo.id,
        relationship_type=RelationshipType.OWNERSHIP,
        workspace_id=workspace_id,
        organization_id=organization_id,
        confidence=0.9,
        evidence_text="Stronger co-occurrence.",
        created_by=user_id,
    )
    await db_session.commit()

    assert second.id == first.id
    assert second.confidence == 0.9
    assert len(fake_graph.relationship_upserts) == 2


# --- ExpertiseInferenceService -----------------------------------------------


async def test_expertise_inference_scores_and_cites_evidence(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    entity_service, relationship_service, _, _ = _services(db_session)
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
    unrelated_person = await entity_service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        entity_type=EntityType.PERSON,
        canonical_name="Bob Example",
        created_by=user_id,
    )
    await db_session.commit()

    for _ in range(3):
        await relationship_service.create(
            workspace_id=workspace_id,
            organization_id=organization_id,
            source_entity_id=person.id,
            target_entity_id=kubernetes.id,
            relationship_type=RelationshipType.MENTIONS,
            confidence=0.8,
            evidence="mentioned in a doc",
            created_by=user_id,
        )
    # A COLLABORATION edge to another PERSON should never surface as
    # "expertise in a person" — only TECHNOLOGY/PRODUCT/PROJECT count.
    await relationship_service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        source_entity_id=person.id,
        target_entity_id=unrelated_person.id,
        relationship_type=RelationshipType.COLLABORATION,
        confidence=0.9,
        created_by=user_id,
    )
    await db_session.commit()

    service = ExpertiseInferenceService(
        relationship_service=relationship_service, entity_service=entity_service
    )
    insights = await service.infer(person.id, workspace_id=workspace_id)

    assert len(insights) == 1
    assert insights[0].canonical_name == "Kubernetes"
    assert insights[0].score > 0
    assert len(insights[0].evidence) == 3
    for reference in insights[0].evidence:
        assert reference.relationship_id is not None


async def test_expertise_inference_returns_nothing_without_evidence(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    entity_service, relationship_service, _, _ = _services(db_session)
    person = await entity_service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        entity_type=EntityType.PERSON,
        canonical_name="Alice Example",
        created_by=user_id,
    )
    await db_session.commit()

    service = ExpertiseInferenceService(
        relationship_service=relationship_service, entity_service=entity_service
    )
    insights = await service.infer(person.id, workspace_id=workspace_id)

    assert insights == []


# --- OwnershipInferenceService -----------------------------------------------


async def test_ownership_inference_writes_edge_above_threshold(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    entity_service, relationship_service, capsule_graph, fake_graph = _services(
        db_session
    )
    person = await entity_service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        entity_type=EntityType.PERSON,
        canonical_name="Alice Example",
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

    service = OwnershipInferenceService(
        relationship_service=relationship_service,
        entity_service=entity_service,
        capsule_graph_service=capsule_graph,
    )
    insights = await service.infer(
        person.id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        created_by=user_id,
    )
    await db_session.commit()

    assert len(insights) == 1
    assert insights[0].canonical_name == "acme/widgets"
    assert insights[0].ownership_category == "repository"
    assert insights[0].share == 1.0
    assert len(fake_graph.relationship_upserts) == 1

    edges = await relationship_service.list_for_entity(
        person.id, workspace_id=workspace_id
    )
    ownership_edges = [
        e for e in edges if e.relationship_type == RelationshipType.OWNERSHIP.value
    ]
    assert len(ownership_edges) == 1


async def test_ownership_inference_skips_below_threshold(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    entity_service, relationship_service, capsule_graph, fake_graph = _services(
        db_session
    )
    person = await entity_service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        entity_type=EntityType.PERSON,
        canonical_name="Alice Example",
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

    # A single, low-confidence mention is not enough evidence to claim
    # ownership (score stays below _MIN_OWNERSHIP_SCORE).
    await relationship_service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        source_entity_id=person.id,
        target_entity_id=repo.id,
        relationship_type=RelationshipType.MENTIONS,
        confidence=0.3,
        created_by=user_id,
    )
    await db_session.commit()

    service = OwnershipInferenceService(
        relationship_service=relationship_service,
        entity_service=entity_service,
        capsule_graph_service=capsule_graph,
    )
    insights = await service.infer(
        person.id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        created_by=user_id,
    )

    assert insights == []
    assert fake_graph.relationship_upserts == []


async def test_ownership_inference_computes_share_across_owners(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    entity_service, relationship_service, capsule_graph, _ = _services(db_session)
    alice = await entity_service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        entity_type=EntityType.PERSON,
        canonical_name="Alice Example",
        created_by=user_id,
    )
    bob = await entity_service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        entity_type=EntityType.PERSON,
        canonical_name="Bob Example",
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

    service = OwnershipInferenceService(
        relationship_service=relationship_service,
        entity_service=entity_service,
        capsule_graph_service=capsule_graph,
    )

    for _ in range(5):
        await relationship_service.create(
            workspace_id=workspace_id,
            organization_id=organization_id,
            source_entity_id=bob.id,
            target_entity_id=repo.id,
            relationship_type=RelationshipType.REFERENCES,
            confidence=1.0,
            created_by=user_id,
        )
    await db_session.commit()
    await service.infer(
        bob.id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        created_by=user_id,
    )
    await db_session.commit()

    for _ in range(5):
        await relationship_service.create(
            workspace_id=workspace_id,
            organization_id=organization_id,
            source_entity_id=alice.id,
            target_entity_id=repo.id,
            relationship_type=RelationshipType.REFERENCES,
            confidence=1.0,
            created_by=user_id,
        )
    await db_session.commit()
    alice_insights = await service.infer(
        alice.id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        created_by=user_id,
    )
    await db_session.commit()

    assert alice_insights[0].share == 0.5
