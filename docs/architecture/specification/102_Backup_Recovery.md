# 102 — Backup and Recovery

## Purpose

This document defines Cerebrum's Backup Strategy across the polyglot persistence stack and its Disaster Recovery procedures. It elaborates [42_Database_Responsibilities.md](42_Database_Responsibilities.md) (Part 4) with the operational backup discipline that document's storage architecture depends on for durability guarantees to hold in practice, not only in principle.

## Scope

This document covers backup and disaster recovery strategy. It does not redefine the datastore responsibilities themselves (see [42_Database_Responsibilities.md](42_Database_Responsibilities.md)) or the Retention Sweep/soft-delete governance (see [47_Data_Governance.md](47_Data_Governance.md)), which governs *intentional* deletion, distinct from this document's concern with *unintentional* data loss.

## Definitions

- **Point-in-Time Recovery (PITR)** — The ability to restore a datastore to its exact state at any specific past moment, not only to the state at the most recent full backup.
- **Restore Verification** — Confirming a backup can actually be successfully restored, distinct from merely confirming the backup process completed without error.

## Backup Strategy

Support: Database Backup, Object Storage Backup, Configuration Backup, Graph Backup, Vector Backup, Scheduled Backup, Restore Verification.

| Backup Type | Datastore | Notes |
|---|---|---|
| Database Backup | PostgreSQL | The highest-priority backup target given PostgreSQL's role as the authoritative store for tenancy, permissions, and audit ([41_Data_Architecture.md](41_Data_Architecture.md)) — PostgreSQL is also the "first write" for every composite entity, per that document's consistency resolution, making its backup completeness the anchor for reconstructing derived state elsewhere. |
| Object Storage Backup | MinIO | Original document binaries; per [42_Database_Responsibilities.md](42_Database_Responsibilities.md), the sole store for this content class, with no PostgreSQL-side duplicate to fall back on if lost. |
| Configuration Backup | PostgreSQL (Configuration Domain data) | Distinct line item despite living in PostgreSQL, given its outsized operational impact if lost — a lost Configuration Backup could leave a restored system technically data-complete but behaviorally misconfigured. |
| Graph Backup | Neo4j | Per [41_Data_Architecture.md](41_Data_Architecture.md), Neo4j is Derived Data relative to PostgreSQL — in principle reconstructable by re-running extraction, but Graph Backup is still required because full reconstruction at enterprise scale (millions of relationships, [41_Data_Architecture.md](41_Data_Architecture.md)) would be prohibitively slow and costly compared to restoring a backup. |
| Vector Backup | Qdrant | Same rationale as Graph Backup — technically Derived Data, but re-embedding millions of Chunks from scratch is a recovery path of last resort, not a first-choice recovery strategy. |
| Scheduled Backup | All of the above | Backups run on a defined recurring schedule (Deferred to Architecture for frequency, per [104_Open_Questions.md](104_Open_Questions.md)), not only on-demand. |
| Restore Verification | All of the above | See definition above — a backup that has never been test-restored is an unverified assumption, not a functioning safety net. |

## Backup Priority and Recovery Point Objective Implications

PostgreSQL and MinIO warrant the tightest Recovery Point Objective (RPO — the maximum acceptable data loss window) given they hold non-reconstructable authoritative data. Neo4j and Qdrant, being Derived Data, can tolerate a wider RPO if their specific restore path is unavailable, since — as a fallback of last resort — the Background Processing Layer's Ingestion-to-Index Workflow ([36_Background_Processing.md](36_Background_Processing.md)) can regenerate them from PostgreSQL's authoritative content, at the reconstruction-time cost noted above. This priority ordering is a direct consequence of [41_Data_Architecture.md](41_Data_Architecture.md)'s Canonical Storage Model, not an independent judgment call this document introduces.

## Disaster Recovery

Support: Point-in-Time Recovery, Backup Validation, Disaster Recovery Procedures, Recovery Documentation, Recovery Testing.

| Element | Description |
|---|---|
| Point-in-Time Recovery | See definition above — required at minimum for PostgreSQL, given its transactional, audit-evidentiary role ([75_Security_Architecture.md](75_Security_Architecture.md)'s Immutable Audit Logs rationale would be undermined by a recovery mechanism that could only restore to a full-backup boundary, potentially losing or duplicating audit records at the recovery point). |
| Backup Validation | Automated checks confirming a completed backup is structurally valid (not merely "the backup job exited zero") — a lighter-weight, more frequent check than full Restore Verification. |
| Disaster Recovery Procedures | Documented, step-by-step procedures for each disaster scenario (datastore corruption, full region loss, accidental mass deletion), maintained as Runbooks per [100_Documentation_Standards.md](100_Documentation_Standards.md). |
| Recovery Documentation | The specific documentation artifact capturing these procedures — overlaps with, and is realized through, [100_Documentation_Standards.md](100_Documentation_Standards.md)'s Runbooks artifact type. |
| Recovery Testing | Periodically executing Disaster Recovery Procedures against a non-production environment to confirm they still work as documented — the DR-specific application of the same Restore Verification discipline, exercised at full-procedure scope rather than single-backup scope. |

## Responsibilities

- Every new datastore added to the Canonical Storage Model in a later phase ([41_Data_Architecture.md](41_Data_Architecture.md)) must receive a corresponding Backup Strategy entry in this document before being considered production-ready.
- Restore Verification and Recovery Testing must be performed on a recurring schedule, not only once at initial setup — an untested backup/recovery procedure degrades in reliability confidence over time as the surrounding system changes.

## Constraints

- This document does not specify exact backup frequency, retention period, or RPO/RTO (Recovery Time Objective) numeric targets — Deferred to Architecture/operations.
- This document does not specify the backup storage location or redundancy strategy (e.g., cross-region replication) — Deferred to Architecture, related to the data residency question in Open Question 3 of [11_Open_Questions.md](11_Open_Questions.md).

## Future Considerations

- As the multi-tenancy model resolves (Open Question 38 in [40_Open_Questions.md](40_Open_Questions.md), resolved in [46_Multi_Tenancy.md](46_Multi_Tenancy.md)), backup/restore procedures should be evaluated for whether single-tenant restoration (restoring one organization's data without affecting others) is required as a distinct capability from full-system restoration — a materially different and more complex recovery scenario given the shared-schema-with-RLS isolation model.

## Acceptance Criteria

- [ ] All seven Backup Strategy elements from the governing specification are defined and mapped to a specific datastore.
- [ ] Backup priority (RPO implications) is explicitly derived from [41_Data_Architecture.md](41_Data_Architecture.md)'s existing authoritative-vs-derived data distinction, not introduced as a new, independent judgment.
- [ ] All five Disaster Recovery elements from the governing specification are defined.
