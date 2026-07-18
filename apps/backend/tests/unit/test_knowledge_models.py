"""Proves CIS Phase 2 Prompt 1's acceptance criteria "Business entities
persist correctly" and "Versioning works" at the ORM level — the
circular Document/DocumentVersion foreign key, optimistic locking, and
soft delete/restore, against the in-memory SQLite pattern established in
apps/backend/tests/conftest.py.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm.exc import StaleDataError

from cerebrum.infrastructure.database.models.collection import (
    Collection,
    CollectionDocument,
)
from cerebrum.infrastructure.database.models.document import Document
from cerebrum.infrastructure.database.models.document_metadata import (
    DocumentMetadata,
)
from cerebrum.infrastructure.database.models.document_version import DocumentVersion
from cerebrum.infrastructure.database.models.folder import Folder
from cerebrum.infrastructure.database.models.organization import Organization
from cerebrum.infrastructure.database.models.tag import DocumentTag, Tag
from cerebrum.infrastructure.database.models.workspace import Workspace

pytestmark = pytest.mark.unit


async def _seed_workspace(session: AsyncSession) -> Workspace:
    org = Organization(name="Acme", slug="acme")
    session.add(org)
    await session.flush()
    ws = Workspace(organization_id=org.id, name="Default", slug="default")
    session.add(ws)
    await session.flush()
    return ws


async def test_full_document_graph_persists(db_session: AsyncSession) -> None:
    ws = await _seed_workspace(db_session)
    folder = Folder(workspace_id=ws.id, parent_id=None, name="Reports")
    db_session.add(folder)
    await db_session.flush()

    document = Document(workspace_id=ws.id, folder_id=folder.id, name="Q1.pdf")
    db_session.add(document)
    await db_session.flush()

    version = DocumentVersion(document_id=document.id, version_number=1)
    db_session.add(version)
    await db_session.flush()

    metadata = DocumentMetadata(
        document_version_id=version.id,
        mime_type="application/pdf",
        file_size_bytes=1024,
        sha256_checksum="a" * 64,
        storage_path="ws/doc/v1.pdf",
        original_filename="Q1.pdf",
        uploaded_filename="q1-uuid.pdf",
        uploaded_at=datetime.now(UTC),
    )
    db_session.add(metadata)
    document.current_version_id = version.id
    version.is_current = True
    await db_session.commit()

    assert document.current_version_id == version.id
    assert version.is_current is True


async def test_optimistic_lock_rejects_a_stale_concurrent_update(
    db_session: AsyncSession, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """Two independent sessions load the same folder; the second
    session's commit, after the first already changed the row, must
    raise :class:`~sqlalchemy.orm.exc.StaleDataError` rather than
    silently overwriting the first writer's change.
    """
    ws = await _seed_workspace(db_session)
    folder = Folder(workspace_id=ws.id, parent_id=None, name="Reports")
    db_session.add(folder)
    await db_session.commit()
    folder_id = folder.id

    async with db_session_factory() as session_a, db_session_factory() as session_b:
        folder_a = await session_a.get(Folder, folder_id)
        folder_b = await session_b.get(Folder, folder_id)
        assert folder_a is not None and folder_b is not None

        folder_a.name = "Renamed by A"
        await session_a.commit()

        folder_b.name = "Renamed by B"
        with pytest.raises(StaleDataError):
            await session_b.commit()


async def test_folder_soft_delete_and_restore(db_session: AsyncSession) -> None:
    ws = await _seed_workspace(db_session)
    folder = Folder(workspace_id=ws.id, parent_id=None, name="Reports")
    db_session.add(folder)
    await db_session.commit()

    assert folder.is_deleted is False
    folder.is_deleted = True
    from cerebrum.utils.clock import utcnow

    folder.deleted_at = utcnow()
    await db_session.commit()
    assert folder.deleted_at is not None

    folder.is_deleted = False
    folder.deleted_at = None
    await db_session.commit()
    assert folder.is_deleted is False


async def test_document_tag_and_collection_associations(
    db_session: AsyncSession,
) -> None:
    ws = await _seed_workspace(db_session)
    document = Document(workspace_id=ws.id, folder_id=None, name="Doc.txt")
    db_session.add(document)
    tag = Tag(workspace_id=ws.id, name="finance")
    db_session.add(tag)
    collection = Collection(workspace_id=ws.id, name="Q1")
    db_session.add(collection)
    await db_session.flush()

    db_session.add(DocumentTag(document_id=document.id, tag_id=tag.id))
    db_session.add(
        CollectionDocument(collection_id=collection.id, document_id=document.id)
    )
    await db_session.commit()  # must not raise
