"""Proves CIS Phase 3 Prompt 1's ``EntityService``: CRUD, soft delete/
restore, history, and dedup-aware ``upsert_from_extraction`` (creating a
new row vs. merging into an existing one — new alias, raised confidence,
appended provenance) against a real database.
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.knowledge_graph.entity_service import EntityService
from cerebrum.infrastructure.database.models.entity import EntityType
from cerebrum.infrastructure.database.models.organization import Organization
from cerebrum.infrastructure.database.models.workspace import Workspace
from cerebrum.infrastructure.entities.results import ExtractedEntity
from cerebrum.repositories.contracts import Pagination
from cerebrum.repositories.postgres.entity_repository import EntityRepository
from cerebrum.shared.errors.exceptions import NotFoundException

pytestmark = pytest.mark.unit


def _service(session: AsyncSession) -> EntityService:
    return EntityService(entity_repository=EntityRepository(session))


async def _seed(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    org = Organization(name="Acme", slug="acme")
    session.add(org)
    await session.flush()
    ws = Workspace(organization_id=org.id, name="Default", slug="default")
    session.add(ws)
    await session.commit()
    return ws.id, org.id


def _candidate(canonical_name: str, confidence: float = 0.7) -> ExtractedEntity:
    return ExtractedEntity(
        entity_type=EntityType.ORGANIZATION,
        canonical_name=canonical_name,
        confidence=confidence,
        context=canonical_name,
        start_offset=0,
        end_offset=len(canonical_name),
    )


async def test_create_and_get(db_session: AsyncSession) -> None:
    ws_id, org_id = await _seed(db_session)
    service = _service(db_session)

    entity = await service.create(
        workspace_id=ws_id,
        organization_id=org_id,
        entity_type=EntityType.PERSON,
        canonical_name="Alice Johnson",
    )
    await db_session.commit()

    fetched = await service.get(entity.id, workspace_id=ws_id)
    assert fetched.canonical_name == "Alice Johnson"
    assert fetched.confidence == 1.0


async def test_get_rejects_a_different_workspace(db_session: AsyncSession) -> None:
    ws_id, org_id = await _seed(db_session)
    service = _service(db_session)
    entity = await service.create(
        workspace_id=ws_id,
        organization_id=org_id,
        entity_type=EntityType.PERSON,
        canonical_name="Alice",
    )
    await db_session.commit()

    with pytest.raises(NotFoundException):
        await service.get(entity.id, workspace_id=uuid.uuid4())


async def test_soft_delete_then_restore(db_session: AsyncSession) -> None:
    ws_id, org_id = await _seed(db_session)
    service = _service(db_session)
    entity = await service.create(
        workspace_id=ws_id,
        organization_id=org_id,
        entity_type=EntityType.PERSON,
        canonical_name="Alice",
    )
    await db_session.commit()

    await service.soft_delete(entity.id, workspace_id=ws_id)
    await db_session.commit()
    with pytest.raises(NotFoundException):
        await service.get(entity.id, workspace_id=ws_id)

    restored = await service.restore(entity.id, workspace_id=ws_id)
    assert restored.id == entity.id


async def test_upsert_from_extraction_creates_a_new_entity_the_first_time(
    db_session: AsyncSession,
) -> None:
    ws_id, org_id = await _seed(db_session)
    service = _service(db_session)
    chunk_id, document_id = uuid.uuid4(), uuid.uuid4()

    entity, was_created = await service.upsert_from_extraction(
        _candidate("Acme Corp"),
        workspace_id=ws_id,
        organization_id=org_id,
        source_chunk_id=chunk_id,
        source_document_id=document_id,
        extractor_name="TestExtractor",
    )
    await db_session.commit()

    assert was_created is True
    assert entity.canonical_name == "Acme Corp"
    assert len(entity.provenance) == 1
    assert entity.provenance[0]["extractor"] == "TestExtractor"
    assert entity.provenance[0]["chunk_id"] == str(chunk_id)


async def test_upsert_from_extraction_merges_into_an_existing_match(
    db_session: AsyncSession,
) -> None:
    ws_id, org_id = await _seed(db_session)
    service = _service(db_session)

    first, _ = await service.upsert_from_extraction(
        _candidate("Acme Corp", confidence=0.6),
        workspace_id=ws_id,
        organization_id=org_id,
        source_chunk_id=uuid.uuid4(),
        source_document_id=uuid.uuid4(),
        extractor_name="Regex",
    )
    await db_session.commit()

    second, was_created = await service.upsert_from_extraction(
        _candidate("Acme Corporation", confidence=0.9),  # similar enough, higher conf
        workspace_id=ws_id,
        organization_id=org_id,
        source_chunk_id=uuid.uuid4(),
        source_document_id=uuid.uuid4(),
        extractor_name="Dictionary",
        similarity_threshold=0.5,
    )
    await db_session.commit()

    assert was_created is False
    assert second.id == first.id
    assert "Acme Corporation" in second.aliases
    assert second.confidence == 0.9
    assert len(second.provenance) == 2


async def test_get_history_returns_provenance(db_session: AsyncSession) -> None:
    ws_id, org_id = await _seed(db_session)
    service = _service(db_session)
    entity, _ = await service.upsert_from_extraction(
        _candidate("Acme Corp"),
        workspace_id=ws_id,
        organization_id=org_id,
        source_chunk_id=uuid.uuid4(),
        source_document_id=uuid.uuid4(),
        extractor_name="Regex",
    )
    await db_session.commit()

    history = await service.get_history(entity.id, workspace_id=ws_id)
    assert len(history) == 1


async def test_list_in_workspace_scopes_to_workspace(db_session: AsyncSession) -> None:
    ws_id, org_id = await _seed(db_session)
    service = _service(db_session)
    await service.create(
        workspace_id=ws_id,
        organization_id=org_id,
        entity_type=EntityType.PERSON,
        canonical_name="Alice",
    )
    await db_session.commit()

    page = await service.list_in_workspace(
        workspace_id=ws_id, pagination=Pagination(page=1, page_size=10)
    )
    assert page.total_items == 1
