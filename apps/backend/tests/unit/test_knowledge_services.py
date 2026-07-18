"""Proves CIS Phase 2 Prompt 1's Validation requirements at the service
layer: duplicate names, folder hierarchy (no cycles), and version
consistency — the checks that live above the database's own constraints.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.knowledge.collection_service import CollectionService
from cerebrum.application.knowledge.document_service import DocumentService
from cerebrum.application.knowledge.folder_service import FolderService
from cerebrum.application.knowledge.version_service import VersionService
from cerebrum.infrastructure.database.models.document_version import VersionType
from cerebrum.infrastructure.database.models.organization import Organization
from cerebrum.infrastructure.database.models.user import User
from cerebrum.infrastructure.database.models.workspace import Workspace
from cerebrum.repositories.postgres.collection_repository import CollectionRepository
from cerebrum.repositories.postgres.document_metadata_repository import (
    DocumentMetadataRepository,
)
from cerebrum.repositories.postgres.document_repository import DocumentRepository
from cerebrum.repositories.postgres.document_version_repository import (
    DocumentVersionRepository,
)
from cerebrum.repositories.postgres.folder_repository import FolderRepository
from cerebrum.repositories.postgres.label_repository import LabelRepository
from cerebrum.repositories.postgres.tag_repository import TagRepository
from cerebrum.shared.errors.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)

pytestmark = pytest.mark.unit


async def _seed(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    org = Organization(name="Acme", slug="acme")
    session.add(org)
    await session.flush()
    ws = Workspace(organization_id=org.id, name="Default", slug="default")
    session.add(ws)
    user = User(
        organization_id=org.id,
        email="alice@example.com",
        hashed_password="x",
        is_active=True,
    )
    session.add(user)
    await session.flush()
    await session.commit()
    return ws.id, user.id


def _folder_service(session: AsyncSession) -> FolderService:
    return FolderService(FolderRepository(session))


def _document_service(session: AsyncSession) -> DocumentService:
    return DocumentService(
        document_repository=DocumentRepository(session),
        folder_repository=FolderRepository(session),
        tag_repository=TagRepository(session),
        label_repository=LabelRepository(session),
    )


def _version_service(session: AsyncSession) -> VersionService:
    return VersionService(
        version_repository=DocumentVersionRepository(session),
        metadata_repository=DocumentMetadataRepository(session),
        document_repository=DocumentRepository(session),
    )


async def test_folder_rejects_duplicate_name_in_same_parent(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    folders = _folder_service(db_session)
    await folders.create(
        workspace_id=ws_id, parent_id=None, name="Reports", created_by=user_id
    )
    await db_session.commit()

    with pytest.raises(ConflictException):
        await folders.create(
            workspace_id=ws_id, parent_id=None, name="Reports", created_by=user_id
        )


async def test_folder_move_rejects_moving_into_own_descendant(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    folders = _folder_service(db_session)
    parent = await folders.create(
        workspace_id=ws_id, parent_id=None, name="Parent", created_by=user_id
    )
    await db_session.commit()
    child = await folders.create(
        workspace_id=ws_id, parent_id=parent.id, name="Child", created_by=user_id
    )
    await db_session.commit()

    with pytest.raises(ValidationException):
        await folders.move(
            parent.id, workspace_id=ws_id, new_parent_id=child.id, updated_by=user_id
        )


async def test_folder_move_rejects_moving_into_self(db_session: AsyncSession) -> None:
    ws_id, user_id = await _seed(db_session)
    folders = _folder_service(db_session)
    folder = await folders.create(
        workspace_id=ws_id, parent_id=None, name="Reports", created_by=user_id
    )
    await db_session.commit()

    with pytest.raises(ValidationException):
        await folders.move(
            folder.id, workspace_id=ws_id, new_parent_id=folder.id, updated_by=user_id
        )


async def test_folder_from_a_different_workspace_is_not_found(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    other_org = Organization(name="Other", slug="other")
    db_session.add(other_org)
    await db_session.flush()
    other_ws = Workspace(organization_id=other_org.id, name="Other WS", slug="other-ws")
    db_session.add(other_ws)
    await db_session.commit()

    folders = _folder_service(db_session)
    folder = await folders.create(
        workspace_id=ws_id, parent_id=None, name="Reports", created_by=user_id
    )
    await db_session.commit()

    with pytest.raises(NotFoundException):
        await folders.get(folder.id, workspace_id=other_ws.id)


async def test_document_rejects_duplicate_name_in_same_folder(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    documents = _document_service(db_session)
    await documents.create(
        workspace_id=ws_id, folder_id=None, name="Q1.pdf", created_by=user_id
    )
    await db_session.commit()

    with pytest.raises(ConflictException):
        await documents.create(
            workspace_id=ws_id, folder_id=None, name="Q1.pdf", created_by=user_id
        )


async def test_version_numbers_increment_sequentially(db_session: AsyncSession) -> None:
    ws_id, user_id = await _seed(db_session)
    documents = _document_service(db_session)
    versions = _version_service(db_session)
    document = await documents.create(
        workspace_id=ws_id, folder_id=None, name="Q1.pdf", created_by=user_id
    )
    await db_session.commit()

    first = await versions.create_version(
        document.id,
        workspace_id=ws_id,
        version_type=VersionType.MAJOR,
        change_summary=None,
        mime_type="application/pdf",
        file_size_bytes=100,
        sha256_checksum="a" * 64,
        storage_path="p1",
        original_filename="q1.pdf",
        uploaded_filename="q1.pdf",
        uploaded_at=datetime.now(UTC),
        created_by=user_id,
    )
    await db_session.commit()
    second = await versions.create_version(
        document.id,
        workspace_id=ws_id,
        version_type=VersionType.MINOR,
        change_summary="fix typo",
        mime_type="application/pdf",
        file_size_bytes=101,
        sha256_checksum="b" * 64,
        storage_path="p2",
        original_filename="q1.pdf",
        uploaded_filename="q1-v2.pdf",
        uploaded_at=datetime.now(UTC),
        created_by=user_id,
    )
    await db_session.commit()

    assert first.version_number == 1
    assert second.version_number == 2
    assert second.is_current is True
    assert first.is_current is False


async def test_restore_version_rejects_a_version_from_a_different_document(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    documents = _document_service(db_session)
    versions = _version_service(db_session)
    doc_a = await documents.create(
        workspace_id=ws_id, folder_id=None, name="A.pdf", created_by=user_id
    )
    doc_b = await documents.create(
        workspace_id=ws_id, folder_id=None, name="B.pdf", created_by=user_id
    )
    await db_session.commit()

    version_of_b = await versions.create_version(
        doc_b.id,
        workspace_id=ws_id,
        version_type=VersionType.MAJOR,
        change_summary=None,
        mime_type="text/plain",
        file_size_bytes=10,
        sha256_checksum="c" * 64,
        storage_path="p3",
        original_filename="b.txt",
        uploaded_filename="b.txt",
        uploaded_at=datetime.now(UTC),
        created_by=user_id,
    )
    await db_session.commit()

    with pytest.raises(ValidationException):
        await versions.set_current(doc_a.id, version_of_b.id, workspace_id=ws_id)


async def test_restore_version_makes_an_older_version_current_again(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    documents = _document_service(db_session)
    versions = _version_service(db_session)
    document = await documents.create(
        workspace_id=ws_id, folder_id=None, name="Q1.pdf", created_by=user_id
    )
    await db_session.commit()

    v1 = await versions.create_version(
        document.id,
        workspace_id=ws_id,
        version_type=VersionType.MAJOR,
        change_summary=None,
        mime_type="application/pdf",
        file_size_bytes=100,
        sha256_checksum="a" * 64,
        storage_path="p1",
        original_filename="q1.pdf",
        uploaded_filename="q1.pdf",
        uploaded_at=datetime.now(UTC),
        created_by=user_id,
    )
    await db_session.commit()
    await versions.create_version(
        document.id,
        workspace_id=ws_id,
        version_type=VersionType.MINOR,
        change_summary=None,
        mime_type="application/pdf",
        file_size_bytes=101,
        sha256_checksum="b" * 64,
        storage_path="p2",
        original_filename="q1.pdf",
        uploaded_filename="q1-v2.pdf",
        uploaded_at=datetime.now(UTC),
        created_by=user_id,
    )
    await db_session.commit()

    restored = await versions.set_current(document.id, v1.id, workspace_id=ws_id)
    await db_session.commit()

    assert restored.is_current is True
    refreshed_document = await documents.get(document.id, workspace_id=ws_id)
    assert refreshed_document.current_version_id == v1.id


async def test_collection_bulk_add_skips_documents_from_another_workspace(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    other_org = Organization(name="Other", slug="other2")
    db_session.add(other_org)
    await db_session.flush()
    other_ws = Workspace(
        organization_id=other_org.id, name="Other WS", slug="other-ws2"
    )
    db_session.add(other_ws)
    await db_session.commit()

    documents = _document_service(db_session)
    collections = CollectionService(
        collection_repository=CollectionRepository(db_session),
        document_repository=DocumentRepository(db_session),
    )
    doc = await documents.create(
        workspace_id=ws_id, folder_id=None, name="A.pdf", created_by=user_id
    )
    foreign_doc = await documents.create(
        workspace_id=other_ws.id, folder_id=None, name="B.pdf", created_by=user_id
    )
    collection = await collections.create(
        workspace_id=ws_id, name="Q1", description=None, created_by=user_id
    )
    await db_session.commit()

    succeeded = await collections.add_documents_bulk(
        collection.id, [doc.id, foreign_doc.id, uuid.uuid4()], workspace_id=ws_id
    )

    assert succeeded == 1
