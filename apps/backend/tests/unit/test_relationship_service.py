"""Proves CIS Phase 3 Prompt 1's ``RelationshipService``: CRUD, soft
delete/restore, and dedup-aware ``upsert_from_extraction`` (strengthens
an existing edge rather than duplicating it) against a real database.
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.knowledge_graph.entity_service import EntityService
from cerebrum.application.knowledge_graph.relationship_service import (
    RelationshipService,
)
from cerebrum.infrastructure.database.models.entity import EntityType
from cerebrum.infrastructure.database.models.organization import Organization
from cerebrum.infrastructure.database.models.relationship import RelationshipType
from cerebrum.infrastructure.database.models.workspace import Workspace
from cerebrum.infrastructure.relationships.results import ExtractedRelationship
from cerebrum.repositories.postgres.entity_repository import EntityRepository
from cerebrum.repositories.postgres.relationship_repository import (
    RelationshipRepository,
)
from cerebrum.shared.errors.exceptions import NotFoundException

pytestmark = pytest.mark.unit


def _service(session: AsyncSession) -> RelationshipService:
    return RelationshipService(relationship_repository=RelationshipRepository(session))


async def _seed_two_entities(
    session: AsyncSession,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    org = Organization(name="Acme", slug="acme")
    session.add(org)
    await session.flush()
    ws = Workspace(organization_id=org.id, name="Default", slug="default")
    session.add(ws)
    await session.commit()

    entities = EntityService(entity_repository=EntityRepository(session))
    alice = await entities.create(
        workspace_id=ws.id,
        organization_id=org.id,
        entity_type=EntityType.PERSON,
        canonical_name="Alice",
    )
    bob = await entities.create(
        workspace_id=ws.id,
        organization_id=org.id,
        entity_type=EntityType.PERSON,
        canonical_name="Bob",
    )
    await session.commit()
    return ws.id, org.id, alice.id, bob.id


async def test_create_and_get(db_session: AsyncSession) -> None:
    ws_id, org_id, alice_id, bob_id = await _seed_two_entities(db_session)
    service = _service(db_session)

    relationship = await service.create(
        workspace_id=ws_id,
        organization_id=org_id,
        source_entity_id=alice_id,
        target_entity_id=bob_id,
        relationship_type=RelationshipType.REPORTS_TO,
    )
    await db_session.commit()

    fetched = await service.get(relationship.id, workspace_id=ws_id)
    assert fetched.source_entity_id == alice_id
    assert fetched.target_entity_id == bob_id


async def test_soft_delete_then_restore(db_session: AsyncSession) -> None:
    ws_id, org_id, alice_id, bob_id = await _seed_two_entities(db_session)
    service = _service(db_session)
    relationship = await service.create(
        workspace_id=ws_id,
        organization_id=org_id,
        source_entity_id=alice_id,
        target_entity_id=bob_id,
        relationship_type=RelationshipType.REPORTS_TO,
    )
    await db_session.commit()

    await service.soft_delete(relationship.id, workspace_id=ws_id)
    await db_session.commit()
    with pytest.raises(NotFoundException):
        await service.get(relationship.id, workspace_id=ws_id)

    restored = await service.restore(relationship.id, workspace_id=ws_id)
    assert restored.id == relationship.id


async def test_upsert_from_extraction_creates_then_strengthens(
    db_session: AsyncSession,
) -> None:
    ws_id, org_id, alice_id, bob_id = await _seed_two_entities(db_session)
    service = _service(db_session)
    candidate = ExtractedRelationship(
        source_index=0,
        target_index=1,
        relationship_type=RelationshipType.REPORTS_TO,
        confidence=0.6,
        evidence="Alice reports to Bob.",
    )

    first, was_created_first = await service.upsert_from_extraction(
        candidate,
        source_entity_id=alice_id,
        target_entity_id=bob_id,
        workspace_id=ws_id,
        organization_id=org_id,
        source_chunk_id=uuid.uuid4(),
        source_document_id=uuid.uuid4(),
    )
    await db_session.commit()
    assert was_created_first is True
    assert first.confidence == 0.6

    stronger_candidate = ExtractedRelationship(
        source_index=0,
        target_index=1,
        relationship_type=RelationshipType.REPORTS_TO,
        confidence=0.9,
        evidence="Alice clearly reports to Bob.",
    )
    second, was_created_second = await service.upsert_from_extraction(
        stronger_candidate,
        source_entity_id=alice_id,
        target_entity_id=bob_id,
        workspace_id=ws_id,
        organization_id=org_id,
        source_chunk_id=uuid.uuid4(),
        source_document_id=uuid.uuid4(),
    )
    await db_session.commit()

    assert was_created_second is False
    assert second.id == first.id
    assert second.confidence == 0.9
    assert second.evidence == "Alice clearly reports to Bob."


async def test_list_for_entity_finds_both_directions(db_session: AsyncSession) -> None:
    ws_id, org_id, alice_id, bob_id = await _seed_two_entities(db_session)
    service = _service(db_session)
    await service.create(
        workspace_id=ws_id,
        organization_id=org_id,
        source_entity_id=alice_id,
        target_entity_id=bob_id,
        relationship_type=RelationshipType.REPORTS_TO,
    )
    await db_session.commit()

    for_alice = await service.list_for_entity(alice_id, workspace_id=ws_id)
    for_bob = await service.list_for_entity(bob_id, workspace_id=ws_id)
    assert len(for_alice) == 1
    assert len(for_bob) == 1
