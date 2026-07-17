# 36 — Background Processing Architecture

## Purpose

This document defines the architecture of the Background Processing Layer: how connector synchronization, document processing, embedding generation, entity/relationship extraction, and index updates are executed asynchronously, with retry, dead-letter handling, and scheduling. It elaborates the Background Processing Layer introduced in [30_System_Architecture.md](30_System_Architecture.md) and [31_Component_Architecture.md](31_Component_Architecture.md).

## Scope

This document covers background job architecture: job types, the pipeline they compose into, retry/DLQ/scheduling design, and observability hooks. It does not cover the Celery-vs-Temporal technology decision itself (see [32_Technology_Stack.md](32_Technology_Stack.md)) or the business logic within each job (see the relevant domain in [35_Domain_Architecture.md](35_Domain_Architecture.md)).

## Definitions

- **Task** — A single, independently retryable unit of background work (e.g., "process one document's OCR stage").
- **Workflow** — An ordered composition of tasks representing a multi-stage pipeline (e.g., ingest → extract → chunk → embed → graph-extract → index).
- **Dead Letter Queue (DLQ)** — A holding queue for tasks that have exhausted their retry budget, requiring manual intervention rather than being silently dropped.

## Background Processing Job Categories

| Category | Triggering Domain | Requirement Traceability |
|---|---|---|
| Connector Synchronization | Connector Domain | FR-CN-003, FR-CN-004, FR-CN-005 |
| Document Processing Pipeline | Knowledge Processing Domain | FR-KP-001–010 |
| Embedding Generation | Knowledge Processing Domain | FR-KP-009 |
| Entity/Relationship Extraction | Knowledge Processing Domain, Knowledge Graph Domain | FR-KP-008, FR-KG-001, FR-KG-002 |
| Index Updates | Enterprise Search Domain, Knowledge Graph Domain | FR-ES-001–003, FR-KG-006 |
| Retention/Archival Sweep | Knowledge Storage Domain | FR-KS-004, FR-KS-005 |
| Staleness Detection Sweep | Enterprise Memory Domain | FR-EM-009 |
| Notification Delivery | Notification Domain | FR-NT-001–005 |
| Webhook Delivery | API Domain | FR-AP-005 |
| Analytics Event Aggregation | Analytics Domain | FR-AL-001–006 |

## The Ingestion-to-Index Workflow

The most architecturally significant background workflow is the multi-stage pipeline from raw content to searchable, graph-connected knowledge. It is modeled as a Workflow composed of independently retryable Tasks, so a failure at any stage does not require re-running earlier, already-successful stages:

```
[Connector Sync / Manual Upload]
        |
        v
  Task: Ingest            (Knowledge Ingestion Domain — duplicate/version detection, normalization)
        |
        v
  Task: Extract            (Knowledge Processing Domain — text/image/table extraction, OCR)
        |
        v
  Task: Chunk & Enrich      (Knowledge Processing Domain — chunking, metadata enrichment, keyword/topic extraction)
        |
        v
  Task: Embed               (Knowledge Processing Domain — embedding generation via EmbeddingProviderPort)
        |
        +----------------------------+
        v                            v
  Task: Extract Entities       Task: Index for Search
  (Knowledge Graph Domain)     (Enterprise Search Domain)
        |                            |
        v                            v
  Task: Update Graph          Task: Confirm Indexed
        |                            |
        +-------------+--------------+
                       v
              Task: Quality Validate   (Knowledge Processing Domain — FR-KP-010)
                       |
                       v
              Task: Notify Completion  (Notification Domain — FR-NT-005)
```

The Embed stage fans out into two independent branches (entity/graph extraction and search indexing) that can proceed in parallel and are individually retryable; a failure in graph extraction does not block search availability, and vice versa — this directly implements Fault Tolerance from [04_Project_Principles.md](04_Project_Principles.md) at the pipeline level.

## Retry Policy

- Every Task defines its own retry policy based on its failure profile, distinguishing transient failures (network timeout, rate limit — retried with exponential backoff up to a defined attempt limit) from non-transient failures (malformed content, revoked connector credential — not retried, routed directly to failure handling), per FR-CN-007 and FR-KI-011.
- Retry backoff parameters (base delay, multiplier, maximum attempts) are Deferred to Architecture-time configuration and MAY vary per Task category — an embedding-provider rate-limit retry profile differs from a transient database-connection retry profile.
- A Task's retry count and outcome are recorded as part of its execution record, feeding Connector Activity Logging (FR-CN-009) and Ingestion Reporting (FR-KI-012).

## Dead Letter Queue Readiness

- Every Task category SHALL have a defined Dead Letter Queue: once a Task exhausts its retry budget, it moves to the DLQ rather than being silently dropped, satisfying FR-KI-011's "failed items are retained in a distinct failed state with a reason, not silently dropped."
- DLQ entries are visible to authorized administrators (via the Administration Layer) and individually retriable or dismissible, consistent with FR-KI-011's "an authorized actor can view and retry failed items."
- DLQ depth per Task category is a Monitoring Layer metric (FR-MN-001), and a sustained DLQ growth rate triggers a Monitoring Layer degradation alert (FR-MN-003).

## Scheduling

- **Cron-style scheduling** drives recurring Tasks with no external trigger: Retention/Archival Sweep, Staleness Detection Sweep, and default connector sync intervals (FR-CN-005) not manually triggered.
- **Event-triggered scheduling** drives Tasks initiated by a domain event or user action: a manual sync trigger (FR-CN-005), a manual document upload (FR-KI-001), or a downstream Task in the Ingestion-to-Index Workflow completing.
- A connector's configured sync interval (FR-CN-005) is stored as Configuration Domain state and read by the scheduler at each evaluation interval, rather than being hard-coded per connector.

## Concurrency and Isolation

- Tasks belonging to different Workflow instances (e.g., two different documents being processed) execute independently and concurrently, bounded only by worker pool capacity (see [39_Performance_Targets.md](39_Performance_Targets.md) for scaling detail).
- Tasks belonging to the *same* connector's sync operation are serialized per FR-CN-005's requirement that a manual trigger during an in-progress sync is queued, not run concurrently against the same connector — enforced via a per-connector execution lock at the Connector Domain's application layer, not a Background Processing Layer-wide constraint.

## Observability Hooks

Every Task emits, at minimum, a start event, a completion or failure event, and duration — consumed by the Monitoring Layer (FR-MN-002's ingestion/processing progress requirement) and the Analytics Layer (FR-AL-004 connector analytics). See [38_Observability.md](38_Observability.md) for the full instrumentation contract.

## Responsibilities

- Every new asynchronous capability added in a later phase must be modeled as one or more Tasks composed into the appropriate Workflow, not as ad hoc code running outside the Background Processing Layer's retry/DLQ/observability guarantees.
- Workflow composition (task ordering, fan-out/fan-in points) is owned by the Knowledge Layer's `pipeline/` module (see [33_Directory_Structure.md](33_Directory_Structure.md)), not duplicated per domain.

## Constraints

- This document does not specify exact retry counts, backoff multipliers, or DLQ retention periods — Deferred to Architecture-time configuration.
- This document does not mandate Celery-specific primitives (chains, chords, groups) by name — the Workflow/Task vocabulary here is technology-agnostic per [32_Technology_Stack.md](32_Technology_Stack.md)'s Celery-to-Temporal migration path.

## Future Considerations

- If migrated to Temporal per [32_Technology_Stack.md](32_Technology_Stack.md), the Workflow/Task vocabulary in this document maps directly onto Temporal's native Workflow/Activity concepts, minimizing redesign.
- Workflow-level (not just Task-level) retry — resuming a partially completed multi-stage pipeline from its last successful stage rather than its last successful Task — is a natural evolution once the Celery-to-Temporal migration trigger conditions are met.

## Acceptance Criteria

- [ ] Every background processing category named in the governing specification (connector sync, document processing, embedding generation, entity/relationship extraction, index updates, retry, DLQ, scheduling) is addressed.
- [ ] The Ingestion-to-Index Workflow is described as independently retryable stages, not an atomic all-or-nothing operation.
- [ ] Retry and DLQ behavior is traceable to specific FR IDs from [20_Functional_Requirements.md](20_Functional_Requirements.md).
