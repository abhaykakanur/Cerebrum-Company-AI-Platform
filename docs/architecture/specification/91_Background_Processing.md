# 91 — Background Processing

## Purpose

This document defines the nine named Workers executing Cerebrum's asynchronous work, mapping each to the Task categories already established in [36_Background_Processing.md](36_Background_Processing.md) (Part 3). It elaborates that document's abstract Task/Workflow model with concrete worker identity, giving operations teams a named unit to monitor, scale, and reason about independently.

## Scope

This document covers Worker identity and responsibility. It does not redefine the Task/Workflow orchestration model, retry policy, or DLQ mechanics already fully specified in [36_Background_Processing.md](36_Background_Processing.md) — this document names *who* executes each Task category; that document defines *how* execution, retry, and failure handling work.

## Definitions

- **Worker** — A named, independently deployable and scalable execution pool consuming Tasks of a specific category from the Background Processing Layer's queue, per [32_Technology_Stack.md](32_Technology_Stack.md)'s Celery-based architecture.

## The Nine Workers

| Worker | Task Category (per [36_Background_Processing.md](36_Background_Processing.md)) | Domain |
|---|---|---|
| Connector Worker | Connector Synchronization | Connector Domain |
| OCR Worker | A specialization of Document Processing Pipeline, specifically the OCR Processing stage (FR-KP-003) | Knowledge Processing Domain |
| Embedding Worker | Embedding Generation | Knowledge Processing Domain |
| Entity Worker | A specialization of Entity/Relationship Extraction, specifically entity extraction (FR-KP-008, FR-KG-001) | Knowledge Processing Domain, Knowledge Graph Domain |
| Relationship Worker | A specialization of Entity/Relationship Extraction, specifically relationship extraction and Graph Linking (FR-KG-002) | Knowledge Graph Domain |
| Search Worker | Index Updates | Enterprise Search Domain |
| Analytics Worker | Analytics Event Aggregation | Analytics Domain |
| Notification Worker | Notification Delivery | Notification Domain, [93_Notification_Architecture.md](93_Notification_Architecture.md) |
| Cleanup Worker | Retention/Archival Sweep, Staleness Detection Sweep | Knowledge Storage Domain, Enterprise Memory Domain |

## Worker Independence and Scaling

Per [39_Performance_Targets.md](39_Performance_Targets.md)'s Queue Scaling strategy, each Worker SHALL scale independently based on its own load profile — the Embedding Worker (compute-intensive, GPU/API-call-bound) has a materially different scaling curve than the Notification Worker (I/O-bound, lightweight), and the Connector Worker's load is bursty and driven by external sync schedules rather than internal platform activity. This is why nine distinct Workers exist rather than one undifferentiated worker pool: independent scaling requires independent identity.

## Worker-to-Pipeline-Stage Mapping

Restating [45_Data_Lifecycle.md](45_Data_Lifecycle.md)'s Ingestion-to-Index Workflow with Worker assignment per stage:

```
Connector Sync           → Connector Worker
Ingest / Extract / Chunk → (Knowledge Processing's general pipeline execution, not a single named Worker below)
OCR (conditional)        → OCR Worker
Embed                    → Embedding Worker
   ├── Extract Entities  → Entity Worker
   ├── Update Graph      → Relationship Worker
   └── Index for Search  → Search Worker
Quality Validate         → (Knowledge Processing's general pipeline execution)
Notify Completion        → Notification Worker
```

The fan-out at the Embed stage (independently retryable Entity, Relationship, and Search branches, per [36_Background_Processing.md](36_Background_Processing.md)) is exactly where distinct Worker identity matters most — a Relationship Worker backlog does not block the Search Worker from keeping search fresh, and vice versa.

## Responsibilities

- Every new asynchronous capability introduced in a later phase must be assigned to an existing Worker or justify a new one, following the same "resist proliferation, but don't force an ill-fitting assignment" balance already applied to Component and Role catalogs elsewhere in this specification ([78_RBAC_Model.md](78_RBAC_Model.md), [87_Component_Library.md](87_Component_Library.md)).
- Worker-level metrics (queue depth, processing rate, error rate per Worker) must be exposed to [88_Dashboard_Architecture.md](88_Dashboard_Architecture.md)'s Jobs Queue Status widget at Worker granularity, not only aggregate Background Processing Layer granularity.

## Constraints

- This document does not redefine retry policy, DLQ mechanics, or scheduling — see [36_Background_Processing.md](36_Background_Processing.md).
- This document does not specify Worker deployment topology (process count, container sizing) — Deferred to Architecture/operations, informed by [39_Performance_Targets.md](39_Performance_Targets.md)'s Queue Scaling strategy.

## Future Considerations

- If the Celery-to-Temporal migration described in [32_Technology_Stack.md](32_Technology_Stack.md) occurs, these nine Worker identities map directly onto Temporal Worker pools with minimal conceptual change, since Worker identity here is already independent of the specific queue technology.

## Acceptance Criteria

- [ ] All nine Workers from the governing specification are defined and mapped to a Task category from [36_Background_Processing.md](36_Background_Processing.md).
- [ ] Worker independence and scaling rationale is stated, connecting to [39_Performance_Targets.md](39_Performance_Targets.md)'s existing Queue Scaling strategy.
- [ ] The Worker-to-pipeline-stage mapping is consistent with [45_Data_Lifecycle.md](45_Data_Lifecycle.md)'s Ingestion-to-Index Workflow, not a divergent restatement of it.
