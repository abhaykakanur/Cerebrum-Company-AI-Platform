"""``CapsuleEvidenceRepository``: append-only CRUD over
:class:`~cerebrum.infrastructure.database.models.capsule_evidence.CapsuleEvidenceRecord`
— CIS Phase 5 Prompt 3's Evidence Engine ledger.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.capsule_evidence import (
    CapsuleEvidenceRecord,
)


class CapsuleEvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> CapsuleEvidenceRecord | None:
        return await self._session.get(CapsuleEvidenceRecord, entity_id)

    async def add(self, entity: CapsuleEvidenceRecord) -> CapsuleEvidenceRecord:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def list_by_capsule(
        self, capsule_id: uuid.UUID
    ) -> list[CapsuleEvidenceRecord]:
        statement = (
            select(CapsuleEvidenceRecord)
            .where(CapsuleEvidenceRecord.capsule_id == capsule_id)
            .order_by(CapsuleEvidenceRecord.created_at)
        )
        result = await self._session.execute(statement)
        return list(result.scalars())

    async def list_by_capsule_and_type(
        self, capsule_id: uuid.UUID, *, insight_type: str
    ) -> list[CapsuleEvidenceRecord]:
        statement = (
            select(CapsuleEvidenceRecord)
            .where(
                CapsuleEvidenceRecord.capsule_id == capsule_id,
                CapsuleEvidenceRecord.insight_type == insight_type,
            )
            .order_by(CapsuleEvidenceRecord.created_at)
        )
        result = await self._session.execute(statement)
        return list(result.scalars())

    async def delete_by_capsule_and_types(
        self, capsule_id: uuid.UUID, *, insight_types: list[str]
    ) -> None:
        """Called at the start of every
        cerebrum.application.capsules.employee_knowledge_capsule_service.EmployeeKnowledgeCapsuleService.refresh
        pass to clear the *previous* refresh's expertise/ownership/
        collaboration evidence before writing this pass's — evidence
        must always reflect the current knowledge-graph state, never
        accumulate stale entries across refreshes. ``identity_link``
        evidence is never passed here, so re-linking history survives
        every refresh.
        """
        statement = select(CapsuleEvidenceRecord).where(
            CapsuleEvidenceRecord.capsule_id == capsule_id,
            CapsuleEvidenceRecord.insight_type.in_(insight_types),
        )
        existing = list((await self._session.execute(statement)).scalars())
        for record in existing:
            await self._session.delete(record)
        await self._session.flush()
