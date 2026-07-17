# 92 — Queue Architecture

## Purpose

This document defines the formal Job Lifecycle state machine, the Job Record's eight tracked fields, and the six Queue Features every Worker ([91_Background_Processing.md](91_Background_Processing.md)) relies on. It completes [36_Background_Processing.md](36_Background_Processing.md)'s Task/Workflow model with the explicit lifecycle states that document's Task-level retry/DLQ discussion assumed but did not formally enumerate.

## Scope

This document covers the Job Lifecycle state machine and the queue mechanics supporting it. It does not redefine Worker identity (see [91_Background_Processing.md](91_Background_Processing.md)) or the Ingestion-to-Index Workflow's stage composition (see [36_Background_Processing.md](36_Background_Processing.md), [45_Data_Lifecycle.md](45_Data_Lifecycle.md)).

## Definitions

- **Job** — A single execution instance of a Task ([36_Background_Processing.md](36_Background_Processing.md)'s definition), tracked through this document's lifecycle states from creation to archival.

## Job Lifecycle

Every Job SHALL progress through the following seven states:

```
Created → Queued → Scheduled → Executing → Retry → Completed → Archived
```

| State | Meaning | Transitions To |
|---|---|---|
| Created | The Job exists (per the `Background Job` entity, [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md)) but has not yet entered the queue. | Queued |
| Queued | The Job is in the Background Processing Layer's queue, awaiting Worker availability. | Scheduled (if delayed) or Executing |
| Scheduled | The Job's execution is deliberately delayed to a future time (a Delayed queue feature, below), distinct from simply waiting for Worker capacity. | Executing (when its scheduled time arrives and a Worker is available) |
| Executing | A Worker is actively processing the Job. | Completed (success) or Retry (failure, retry budget remaining) |
| Retry | The Job failed and is awaiting a retry attempt per [36_Background_Processing.md](36_Background_Processing.md)'s backoff policy. | Queued (re-enters the queue for the next attempt) or, if retry budget exhausted, a terminal Dead Letter Queue state (per [36_Background_Processing.md](36_Background_Processing.md); DLQ entries are a distinct terminal outcome from Completed, tracked as failed rather than archived-successful) |
| Completed | The Job finished successfully. | Archived |
| Archived | The Job's record is retained for historical/audit purposes but is no longer active — per [45_Data_Lifecycle.md](45_Data_Lifecycle.md)'s general lifecycle state pattern applied to Jobs specifically. | (Terminal, subject to the same Retention Sweep governance as any other entity, [47_Data_Governance.md](47_Data_Governance.md)) |

A Job that exhausts its DLQ path is not silently lost — per [36_Background_Processing.md](36_Background_Processing.md)'s DLQ Readiness requirement, it remains visible to administrators for manual review/retry, tracked as a distinct outcome from both Completed and the routine Retry cycle.

## Job Record

Every Job SHALL record the following eight fields, extending the `Background Job` entity's definition from [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md):

| Field | Purpose |
|---|---|
| ID | Per the Base Entity Envelope ([44_Global_Entity_Model.md](44_Global_Entity_Model.md)). |
| Status | The current Job Lifecycle state, per the seven states above. |
| Owner | Which Worker ([91_Background_Processing.md](91_Background_Processing.md)) is or was responsible for executing this Job. |
| Duration | Execution time, feeding [88_Dashboard_Architecture.md](88_Dashboard_Architecture.md)'s Jobs Queue Status widget and [38_Observability.md](38_Observability.md)'s Performance Monitoring. |
| Retries | Current and total retry attempt count, per [36_Background_Processing.md](36_Background_Processing.md)'s Retry Policy. |
| Logs | Structured log entries specific to this Job's execution, per [38_Observability.md](38_Observability.md)'s Structured Logging, correlated via the Job's ID. |
| Errors | Any error encountered, classified per [38_Observability.md](38_Observability.md)'s error taxonomy. |
| Progress | For long-running Jobs (e.g., a large connector Full Sync), a completion percentage or item-count progress indicator, feeding FR-MN-002's ingestion/processing progress requirement and [88_Dashboard_Architecture.md](88_Dashboard_Architecture.md)'s display. |

## Queue Features

Support the following six features, extending [36_Background_Processing.md](36_Background_Processing.md)'s Retry Policy and DLQ Readiness with the complete queue-mechanical feature set:

| Feature | Description |
|---|---|
| Priority | Jobs may carry a priority level, allowing time-sensitive work (e.g., a user-triggered manual sync, FR-CN-005) to be processed ahead of routine scheduled background work within the same Worker's queue. |
| Retry | Per [36_Background_Processing.md](36_Background_Processing.md)'s existing Retry Policy — restated here as a queue-level feature, not redefined. |
| Delayed | Supports the Scheduled Job Lifecycle state — a Job may be enqueued now but not eligible for execution until a specified future time. |
| Dead Letter Queue | Per [36_Background_Processing.md](36_Background_Processing.md)'s existing DLQ Readiness — restated here as a queue-level feature. |
| Scheduling | Recurring Job creation per [36_Background_Processing.md](36_Background_Processing.md)'s cron-style scheduling pattern, distinct from the one-time Delayed feature. |
| Monitoring | Every queue exposes depth, throughput, and error-rate metrics per Worker, feeding [38_Observability.md](38_Observability.md) and [88_Dashboard_Architecture.md](88_Dashboard_Architecture.md). |

## Responsibilities

- Every Worker ([91_Background_Processing.md](91_Background_Processing.md)) must populate all eight Job Record fields for every Job it processes — an incomplete Job Record undermines both the Dashboard's Jobs Queue Status widget and operational debugging.
- The Job Lifecycle's seven states must be the exclusive vocabulary used across [88_Dashboard_Architecture.md](88_Dashboard_Architecture.md)'s Jobs Queue Status widget and any administrative Job-inspection UI — no ad hoc, UI-specific status label should diverge from this canonical state list.

## Constraints

- This document does not specify exact priority levels, delay-scheduling granularity, or monitoring metric retention — Deferred to Architecture.
- This document does not redefine the Retry and DLQ mechanics — see [36_Background_Processing.md](36_Background_Processing.md) for their full specification; this document only confirms their status as Queue Features alongside the four new ones (Priority, Delayed, Scheduling, Monitoring).

## Future Considerations

- As Job volume grows, the Archived state's own retention period (per [47_Data_Governance.md](47_Data_Governance.md)'s general Retention Policy pattern) should be tuned specifically for Background Job records, which may warrant a shorter retention than content entities given their primarily operational (not organizational-knowledge) value.

## Acceptance Criteria

- [ ] The seven-state Job Lifecycle from the governing specification is defined as a complete state machine with transitions.
- [ ] All eight Job Record fields from the governing specification are defined.
- [ ] All six Queue Features from the governing specification are defined, with Retry and DLQ explicitly cross-referenced to [36_Background_Processing.md](36_Background_Processing.md) rather than redefined.
