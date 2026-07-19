"""Proves CIS Phase 5 Prompt 3's ``CapsuleRepository``,
``CapsuleEvidenceRepository``, and ``CapsuleTimelineRepository`` against
a real SQLite-backed session — the same "test the real SQL, not a
reimplementation of it" precedent test_workflow_repository.py's
docstring explains.
"""

import uuid
from datetime import timedelta

import pytest
from _auth_factories import create_organization, create_user, create_workspace
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.capsule import EmployeeKnowledgeCapsule
from cerebrum.infrastructure.database.models.capsule_evidence import (
    CapsuleEvidenceRecord,
)
from cerebrum.infrastructure.database.models.capsule_timeline_event import (
    CapsuleTimelineEvent,
)
from cerebrum.infrastructure.database.models.entity import Entity, EntityType
from cerebrum.repositories.contracts import FilterOperator, FilterSpec, Pagination
from cerebrum.repositories.postgres.capsule_evidence_repository import (
    CapsuleEvidenceRepository,
)
from cerebrum.repositories.postgres.capsule_repository import CapsuleRepository
from cerebrum.repositories.postgres.capsule_timeline_repository import (
    CapsuleTimelineRepository,
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


def _capsule(
    *,
    workspace_id: uuid.UUID,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    **overrides,
) -> EmployeeKnowledgeCapsule:
    defaults = {
        "workspace_id": workspace_id,
        "organization_id": organization_id,
        "user_id": user_id,
    }
    defaults.update(overrides)
    return EmployeeKnowledgeCapsule(**defaults)


async def test_add_and_get_capsule(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    repository = CapsuleRepository(db_session)

    created = await repository.add(
        _capsule(
            workspace_id=workspace_id, organization_id=organization_id, user_id=user_id
        )
    )
    await db_session.commit()

    fetched = await repository.get_by_id(created.id)
    assert fetched is not None
    assert fetched.user_id == user_id
    assert fetched.is_stale is True


async def test_get_by_user(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    repository = CapsuleRepository(db_session)
    created = await repository.add(
        _capsule(
            workspace_id=workspace_id, organization_id=organization_id, user_id=user_id
        )
    )
    await db_session.commit()

    found = await repository.get_by_user(user_id, workspace_id=workspace_id)
    assert found is not None
    assert found.id == created.id

    assert await repository.get_by_user(uuid.uuid4(), workspace_id=workspace_id) is None


async def test_soft_delete_and_restore_capsule(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    repository = CapsuleRepository(db_session)
    created = await repository.add(
        _capsule(
            workspace_id=workspace_id, organization_id=organization_id, user_id=user_id
        )
    )
    await db_session.commit()

    await repository.soft_delete(created.id)
    await db_session.commit()
    assert await repository.get_by_id(created.id) is None

    await repository.restore(created.id)
    await db_session.commit()
    assert await repository.get_by_id(created.id) is not None


async def test_list_stale_filters_correctly(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    _, _, other_user_id = await _tenant(db_session)
    repository = CapsuleRepository(db_session)
    person = Entity(
        workspace_id=workspace_id,
        organization_id=organization_id,
        entity_type=EntityType.PERSON.value,
        canonical_name="Alice Example",
    )
    db_session.add(person)
    await db_session.flush()

    stale_and_linked = await repository.add(
        _capsule(
            workspace_id=workspace_id,
            organization_id=organization_id,
            user_id=user_id,
            person_entity_id=person.id,
            is_stale=True,
        )
    )
    await repository.add(
        _capsule(
            workspace_id=workspace_id,
            organization_id=organization_id,
            user_id=other_user_id,
            is_stale=True,
        )
    )
    await db_session.commit()

    stale = await repository.list_stale(workspace_id=workspace_id)

    assert [c.id for c in stale] == [stale_and_linked.id]


async def test_list_filters_by_workspace(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    _, other_workspace_id, other_user_id = await _tenant(db_session)
    repository = CapsuleRepository(db_session)
    await repository.add(
        _capsule(
            workspace_id=workspace_id, organization_id=organization_id, user_id=user_id
        )
    )
    await repository.add(
        _capsule(
            workspace_id=other_workspace_id,
            organization_id=organization_id,
            user_id=other_user_id,
        )
    )
    await db_session.commit()

    page = await repository.list(
        pagination=Pagination(page=1, page_size=50),
        filters=[
            FilterSpec(
                field="workspace_id", operator=FilterOperator.EQ, value=workspace_id
            )
        ],
    )

    assert len(page.items) == 1


async def test_capsule_evidence_repository(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    capsule = await CapsuleRepository(db_session).add(
        _capsule(
            workspace_id=workspace_id, organization_id=organization_id, user_id=user_id
        )
    )
    await db_session.commit()
    repository = CapsuleEvidenceRepository(db_session)

    identity_record = await repository.add(
        CapsuleEvidenceRecord(
            capsule_id=capsule.id,
            insight_type="identity_link",
            insight_key="Alice Example",
            confidence=1.0,
            description="Linked by operator.",
        )
    )
    expertise_record = await repository.add(
        CapsuleEvidenceRecord(
            capsule_id=capsule.id,
            insight_type="expertise",
            insight_key="Kubernetes",
            confidence=0.8,
            description="Co-occurrence evidence.",
        )
    )
    await db_session.commit()

    all_records = await repository.list_by_capsule(capsule.id)
    assert {r.id for r in all_records} == {identity_record.id, expertise_record.id}

    expertise_only = await repository.list_by_capsule_and_type(
        capsule.id, insight_type="expertise"
    )
    assert [r.id for r in expertise_only] == [expertise_record.id]

    await repository.delete_by_capsule_and_types(
        capsule.id, insight_types=["expertise"]
    )
    await db_session.commit()

    remaining = await repository.list_by_capsule(capsule.id)
    assert [r.id for r in remaining] == [identity_record.id]


async def test_capsule_timeline_repository(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    capsule = await CapsuleRepository(db_session).add(
        _capsule(
            workspace_id=workspace_id, organization_id=organization_id, user_id=user_id
        )
    )
    await db_session.commit()
    repository = CapsuleTimelineRepository(db_session)
    now = utcnow()

    older = CapsuleTimelineEvent(
        capsule_id=capsule.id,
        event_type="contribution",
        occurred_at=now - timedelta(days=1),
        title="Older event",
    )
    newer = CapsuleTimelineEvent(
        capsule_id=capsule.id,
        event_type="ownership_change",
        occurred_at=now,
        title="Newer event",
    )
    await repository.replace_for_capsule(capsule.id, [older, newer])
    await db_session.commit()

    page = await repository.list_by_capsule(
        capsule.id, pagination=Pagination(page=1, page_size=50)
    )
    assert page.total_items == 2
    assert [event.title for event in page.items] == ["Newer event", "Older event"]

    replacement = CapsuleTimelineEvent(
        capsule_id=capsule.id,
        event_type="contribution",
        occurred_at=now,
        title="Replacement event",
    )
    await repository.replace_for_capsule(capsule.id, [replacement])
    await db_session.commit()

    page_after_replace = await repository.list_by_capsule(
        capsule.id, pagination=Pagination(page=1, page_size=50)
    )
    assert [event.title for event in page_after_replace.items] == ["Replacement event"]
