"""Proves CIS Phase 4 Prompt 2's ``ConversationRepository`` against a
real SQLite-backed session (see apps/backend/tests/conftest.py's
``db_session`` fixture docstring) rather than a hand-written fake — the
same "test the real SQL, not a reimplementation of it" choice this
codebase makes for every PostgreSQL-backed CRUD service (there is no
``test_document_repository.py`` either; ``DocumentService`` is proven
the same way).
"""

import uuid

import pytest
from _auth_factories import create_organization, create_user, create_workspace
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.conversation import Conversation
from cerebrum.repositories.contracts import Pagination
from cerebrum.repositories.postgres.conversation_repository import (
    ConversationRepository,
)

pytestmark = pytest.mark.unit


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


def _hasher():  # type: ignore[no-untyped-def]
    from cerebrum.config.security import SecuritySettings
    from cerebrum.infrastructure.security.password import PasswordHasher

    return PasswordHasher(SecuritySettings())


def _conversation(
    *,
    workspace_id: uuid.UUID,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    title: str,
) -> Conversation:
    return Conversation(
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        title=title,
        status="active",
    )


async def test_add_and_get_by_id(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    repository = ConversationRepository(db_session)

    created = await repository.add(
        _conversation(
            workspace_id=workspace_id,
            organization_id=organization_id,
            user_id=user_id,
            title="Q1 Planning",
        )
    )
    await db_session.commit()

    fetched = await repository.get_by_id(created.id)
    assert fetched is not None
    assert fetched.title == "Q1 Planning"


async def test_get_by_id_returns_none_when_soft_deleted(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    repository = ConversationRepository(db_session)
    created = await repository.add(
        _conversation(
            workspace_id=workspace_id,
            organization_id=organization_id,
            user_id=user_id,
            title="Temp",
        )
    )
    await db_session.commit()

    await repository.soft_delete(created.id)
    await db_session.commit()

    assert await repository.get_by_id(created.id) is None
    assert await repository.get_by_id_including_deleted(created.id) is not None


async def test_restore_clears_soft_delete(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    repository = ConversationRepository(db_session)
    created = await repository.add(
        _conversation(
            workspace_id=workspace_id,
            organization_id=organization_id,
            user_id=user_id,
            title="Temp",
        )
    )
    await db_session.commit()
    await repository.soft_delete(created.id)
    await db_session.commit()

    await repository.restore(created.id)
    await db_session.commit()

    assert await repository.get_by_id(created.id) is not None


async def test_list_is_scoped_to_workspace_and_excludes_deleted(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    _, other_workspace_id, _ = await _tenant(db_session)
    repository = ConversationRepository(db_session)

    kept = await repository.add(
        _conversation(
            workspace_id=workspace_id,
            organization_id=organization_id,
            user_id=user_id,
            title="Kept",
        )
    )
    deleted = await repository.add(
        _conversation(
            workspace_id=workspace_id,
            organization_id=organization_id,
            user_id=user_id,
            title="Deleted",
        )
    )
    await repository.add(
        _conversation(
            workspace_id=other_workspace_id,
            organization_id=organization_id,
            user_id=user_id,
            title="Other workspace",
        )
    )
    await db_session.commit()
    await repository.soft_delete(deleted.id)
    await db_session.commit()

    from cerebrum.repositories.contracts import FilterOperator, FilterSpec

    page = await repository.list(
        pagination=Pagination(page=1, page_size=50),
        filters=[
            FilterSpec(
                field="workspace_id", operator=FilterOperator.EQ, value=workspace_id
            )
        ],
    )

    assert [c.id for c in page.items] == [kept.id]


async def test_search_by_text_matches_title_or_summary(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    repository = ConversationRepository(db_session)
    title_match = await repository.add(
        _conversation(
            workspace_id=workspace_id,
            organization_id=organization_id,
            user_id=user_id,
            title="Acme Contract Review",
        )
    )
    summary_match = _conversation(
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        title="Unrelated",
    )
    summary_match.summary = "Discussion about the Acme renewal terms."
    await repository.add(summary_match)
    await repository.add(
        _conversation(
            workspace_id=workspace_id,
            organization_id=organization_id,
            user_id=user_id,
            title="Totally different",
        )
    )
    await db_session.commit()

    page = await repository.search_by_text(
        workspace_id=workspace_id,
        query_text="Acme",
        pagination=Pagination(page=1, page_size=50),
    )

    result_ids = {c.id for c in page.items}
    assert title_match.id in result_ids
    assert summary_match.id in result_ids
    assert page.total_items == 2
