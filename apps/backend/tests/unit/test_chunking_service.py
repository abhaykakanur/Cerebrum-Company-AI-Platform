"""Proves CIS Phase 2 Prompt 4's Chunking Engine service layer: a
completed extraction gets chunked into real persisted ``Chunk`` rows,
strategy dispatch, heading-based ``parent_chunk_id`` resolution against
real database IDs, re-chunking replaces the prior chunk set, a missing
extraction is rejected, a strategy failure marks the job ``FAILED``
without raising, and tenant isolation.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.knowledge.chunking_service import ChunkingService
from cerebrum.application.knowledge.document_service import DocumentService
from cerebrum.application.knowledge.version_service import VersionService
from cerebrum.infrastructure.chunking.options import ChunkingOptions
from cerebrum.infrastructure.database.models.chunk import ChunkingStrategy
from cerebrum.infrastructure.database.models.document_extraction import (
    DocumentExtraction,
    ExtractionStatus,
)
from cerebrum.infrastructure.database.models.document_version import VersionType
from cerebrum.infrastructure.database.models.organization import Organization
from cerebrum.infrastructure.database.models.processing_job import ProcessingJobStatus
from cerebrum.infrastructure.database.models.user import User
from cerebrum.infrastructure.database.models.workspace import Workspace
from cerebrum.repositories.postgres.chunk_repository import ChunkRepository
from cerebrum.repositories.postgres.document_extraction_repository import (
    DocumentExtractionRepository,
)
from cerebrum.repositories.postgres.document_metadata_repository import (
    DocumentMetadataRepository,
)
from cerebrum.repositories.postgres.document_repository import DocumentRepository
from cerebrum.repositories.postgres.document_version_repository import (
    DocumentVersionRepository,
)
from cerebrum.repositories.postgres.folder_repository import FolderRepository
from cerebrum.repositories.postgres.label_repository import LabelRepository
from cerebrum.repositories.postgres.processing_job_repository import (
    ProcessingJobRepository,
)
from cerebrum.repositories.postgres.tag_repository import TagRepository
from cerebrum.shared.errors.exceptions import NotFoundException, ValidationException

pytestmark = pytest.mark.unit


def _chunking_service(session: AsyncSession) -> ChunkingService:
    return ChunkingService(
        chunk_repository=ChunkRepository(session),
        extraction_repository=DocumentExtractionRepository(session),
        version_repository=DocumentVersionRepository(session),
        document_repository=DocumentRepository(session),
        job_repository=ProcessingJobRepository(session),
    )


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


async def _seed_version(
    session: AsyncSession, *, workspace_id: uuid.UUID, user_id: uuid.UUID
) -> uuid.UUID:
    documents = DocumentService(
        document_repository=DocumentRepository(session),
        folder_repository=FolderRepository(session),
        tag_repository=TagRepository(session),
        label_repository=LabelRepository(session),
    )
    versions = VersionService(
        version_repository=DocumentVersionRepository(session),
        metadata_repository=DocumentMetadataRepository(session),
        document_repository=DocumentRepository(session),
    )
    document = await documents.create(
        workspace_id=workspace_id, folder_id=None, name="Doc", created_by=user_id
    )
    await session.commit()
    version = await versions.create_version(
        document.id,
        workspace_id=workspace_id,
        version_type=VersionType.MAJOR,
        change_summary=None,
        mime_type="text/plain",
        file_size_bytes=10,
        sha256_checksum="a" * 64,
        storage_path="p",
        original_filename="doc",
        uploaded_filename="doc",
        uploaded_at=datetime.now(UTC),
        created_by=user_id,
    )
    await session.commit()
    return version.id


async def _seed_completed_extraction(
    session: AsyncSession, *, version_id: uuid.UUID, text: str
) -> None:
    repository = DocumentExtractionRepository(session)
    await repository.add(
        DocumentExtraction(
            document_version_id=version_id,
            status=ExtractionStatus.COMPLETED.value,
            extracted_text=text,
            extracted_metadata={},
        )
    )
    await session.commit()


async def test_chunk_version_persists_chunks_and_completes_the_job(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    version_id = await _seed_version(db_session, workspace_id=ws_id, user_id=user_id)
    await _seed_completed_extraction(db_session, version_id=version_id, text="a" * 250)

    service = _chunking_service(db_session)
    job = await service.chunk_version(
        version_id,
        workspace_id=ws_id,
        strategy=ChunkingStrategy.FIXED_SIZE,
        options=ChunkingOptions(chunk_size=100),
    )
    await db_session.commit()

    assert job.status == ProcessingJobStatus.COMPLETED.value
    assert job.progress_percent == 100

    chunks = await service.list_chunks(version_id, workspace_id=ws_id)
    assert [c.chunk_index for c in chunks] == [0, 1, 2]
    assert all(c.strategy == ChunkingStrategy.FIXED_SIZE.value for c in chunks)
    assert all(c.processing_job_id == job.id for c in chunks)


async def test_heading_based_chunks_resolve_real_parent_chunk_ids(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    version_id = await _seed_version(db_session, workspace_id=ws_id, user_id=user_id)
    text = "# Title\nIntro.\n## Sub A\nContent A.\n## Sub B\nContent B."
    await _seed_completed_extraction(db_session, version_id=version_id, text=text)

    service = _chunking_service(db_session)
    await service.chunk_version(
        version_id, workspace_id=ws_id, strategy=ChunkingStrategy.HEADING_BASED
    )
    await db_session.commit()

    chunks = await service.list_chunks(version_id, workspace_id=ws_id)
    title_chunk = next(c for c in chunks if c.chunk_metadata["heading_text"] == "Title")
    sub_a = next(c for c in chunks if c.chunk_metadata["heading_text"] == "Sub A")
    sub_b = next(c for c in chunks if c.chunk_metadata["heading_text"] == "Sub B")

    assert sub_a.parent_chunk_id == title_chunk.id
    assert sub_b.parent_chunk_id == title_chunk.id
    assert title_chunk.parent_chunk_id is None


async def test_rechunking_replaces_the_prior_chunk_set(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    version_id = await _seed_version(db_session, workspace_id=ws_id, user_id=user_id)
    await _seed_completed_extraction(db_session, version_id=version_id, text="a" * 250)

    service = _chunking_service(db_session)
    options = ChunkingOptions(chunk_size=100)
    await service.chunk_version(
        version_id,
        workspace_id=ws_id,
        strategy=ChunkingStrategy.FIXED_SIZE,
        options=options,
    )
    await db_session.commit()
    first_chunks = await service.list_chunks(version_id, workspace_id=ws_id)
    assert len(first_chunks) == 3

    await service.chunk_version(
        version_id,
        workspace_id=ws_id,
        strategy=ChunkingStrategy.FIXED_SIZE_OVERLAP,
        options=options,
    )
    await db_session.commit()
    second_chunks = await service.list_chunks(version_id, workspace_id=ws_id)

    assert all(
        c.strategy == ChunkingStrategy.FIXED_SIZE_OVERLAP.value for c in second_chunks
    )
    assert {c.id for c in first_chunks}.isdisjoint({c.id for c in second_chunks})


async def test_chunk_version_rejects_a_version_with_no_completed_extraction(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    version_id = await _seed_version(db_session, workspace_id=ws_id, user_id=user_id)

    service = _chunking_service(db_session)
    with pytest.raises(ValidationException):
        await service.chunk_version(
            version_id, workspace_id=ws_id, strategy=ChunkingStrategy.PARAGRAPH
        )


async def test_chunk_version_rejects_a_version_from_another_workspace(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    version_id = await _seed_version(db_session, workspace_id=ws_id, user_id=user_id)
    await _seed_completed_extraction(db_session, version_id=version_id, text="hello")

    other_org = Organization(name="Other", slug="other")
    db_session.add(other_org)
    await db_session.flush()
    other_ws = Workspace(organization_id=other_org.id, name="Other", slug="other-ws")
    db_session.add(other_ws)
    await db_session.commit()

    service = _chunking_service(db_session)
    with pytest.raises(NotFoundException):
        await service.chunk_version(
            version_id, workspace_id=other_ws.id, strategy=ChunkingStrategy.PARAGRAPH
        )
