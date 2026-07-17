# 67 — Connector Lifecycle

## Purpose

This document defines the complete lifecycle a connector instance progresses through, from creation to deletion, mapping each stage to its owning component from [65_Connector_Architecture.md](65_Connector_Architecture.md). It extends [45_Data_Lifecycle.md](45_Data_Lifecycle.md)'s Document Lifecycle with the connector-instance-level stages that precede and govern every document that connector ever syncs.

## Scope

This document covers connector-instance lifecycle sequencing. It does not cover the per-document lifecycle once content is fetched (see [45_Data_Lifecycle.md](45_Data_Lifecycle.md), stage "Connector-Sourced Ingestion" onward) or synchronization mechanics within the recurring sync stages (see [68_Synchronization_Architecture.md](68_Synchronization_Architecture.md)).

## Definitions

- **Connector Instance** — A specific, configured connection to one source system (e.g., "Engineering Team's Slack workspace"), as distinct from the Connector Plugin (the reusable code implementing a category, per [66_Connector_SDK.md](66_Connector_SDK.md)).

## The Connector Lifecycle

Every Connector Instance SHALL progress through the following fourteen stages:

| # | Stage | Owning Component | Notes |
|---|---|---|---|
| 1 | Connector Created | Connector Configuration Manager | An authorized actor configures a new Connector Instance, selecting a category from [65_Connector_Architecture.md](65_Connector_Architecture.md)'s catalog (FR-CN-001's precondition). |
| 2 | Authentication | Authentication Layer | Credential exchange with the source system (FR-CN-001). |
| 3 | Validation | Connector Configuration Manager | Connection validation before sync is enabled (FR-CN-002). |
| 4 | Permission Verification | Permission Synchronization Engine | Confirms Cerebrum's granted access scope at the source system matches the configured Connector Instance's intended scope, before any content is fetched — a new, explicit gate not previously named at this granularity in Part 2/3, added here to prevent a misconfigured connector from silently under- or over-scoping access. |
| 5 | Metadata Discovery | Metadata Extraction Engine | An initial, lightweight pass identifying the shape and volume of content in scope (folder structure, item counts) before committing to a full content fetch — informs sync planning and progress estimation (FR-MN-002). |
| 6 | Initial Full Sync | Synchronization Engine | FR-CN-003. |
| 7 | Index Creation | (Handoff to Knowledge Processing/Enterprise Search Domains) | The point at which the first synced content becomes available for retrieval, per [45_Data_Lifecycle.md](45_Data_Lifecycle.md)'s "Available for Retrieval" gate, applied here at the connector level (all-content-synced) rather than per-document. |
| 8 | Health Monitoring | Health Monitor | Continuous, from this point onward — not a one-time stage but an ongoing state overlapping every subsequent stage. |
| 9 | Incremental Synchronization | Synchronization Engine, Delta Detection Engine | FR-CN-004; the connector's steady-state operating stage, recurring per its configured schedule (FR-CN-005). |
| 10 | Failure Recovery | Retry Engine | Entered from Incremental Synchronization (or any stage) on failure, per [68_Synchronization_Architecture.md](68_Synchronization_Architecture.md)'s Retry Strategy; returns to Incremental Synchronization on success. |
| 11 | Configuration Updates | Connector Configuration Manager | An authorized actor modifies scope, schedule, or other configuration (FR-CN-005); may re-trigger stages 3–5 if the change is scope-affecting. |
| 12 | Version Updates | Connector Configuration Manager | The underlying Connector Plugin is upgraded to a new Connector Version, per [66_Connector_SDK.md](66_Connector_SDK.md) — the Connector Instance's configuration and synced content persist across this transition. |
| 13 | Archival | Connector Configuration Manager | The Connector Instance is paused (no further sync) but its previously synced content remains per [45_Data_Lifecycle.md](45_Data_Lifecycle.md)'s Archived state — mirrors Workspace Archival (FR-WS-006) at the connector level. |
| 14 | Deletion | Connector Configuration Manager | Soft-deleted first, hard-deleted only via Retention Sweep, per [47_Data_Governance.md](47_Data_Governance.md)'s binding rule — previously synced content's deletion follows [45_Data_Lifecycle.md](45_Data_Lifecycle.md)'s own Document deletion cascade, not an immediate bulk purge. |

## Lifecycle State Diagram (Descriptive)

```
Created → Authentication → Validation → Permission Verification → Metadata Discovery
    → Initial Full Sync → Index Creation
    → [Health Monitoring: continuous from here]
    → Incremental Synchronization ⇄ Failure Recovery
    → Configuration Updates (may loop back to Validation)
    → Version Updates (returns to Incremental Synchronization)
    → Archival → Deletion
```

Configuration Updates and Version Updates are re-entrant states — a healthy, steadily syncing connector may cycle through either any number of times without leaving the Incremental Synchronization stage's overall operating regime, consistent with [45_Data_Lifecycle.md](45_Data_Lifecycle.md)'s Document Lifecycle's own re-entrant "Version Updates" pattern.

## Responsibilities

- Every Connector Plugin implementation must support all fourteen lifecycle stages via the SDK contract's capabilities ([66_Connector_SDK.md](66_Connector_SDK.md)); a plugin unable to support a stage (e.g., no meaningful Permission Verification for a Local Upload source) must document the no-op rationale per that document's rule.
- Stage 4 (Permission Verification) is a hard gate — a Connector Instance failing this check SHALL NOT proceed to Metadata Discovery or Initial Full Sync, preventing over-scoped access from ever reaching content-fetch stages.

## Constraints

- This document does not specify the exact UI/workflow an administrator experiences configuring a connector — a Frontend Layer and Administration Domain concern outside this document's architecture-only scope.
- Stage timing/duration targets are not specified here — Deferred to Architecture, informed by [39_Performance_Targets.md](39_Performance_Targets.md)'s general scalability strategy.

## Future Considerations

- As the connector catalog grows (per [65_Connector_Architecture.md](65_Connector_Architecture.md)), category-specific lifecycle variants may prove necessary (e.g., a Database connector's "Metadata Discovery" differs materially in shape from a Slack connector's) while preserving the fourteen-stage sequence's overall structure.

## Acceptance Criteria

- [ ] All fourteen lifecycle stages from the governing specification are represented with an owning component.
- [ ] Re-entrant stages (Configuration Updates, Version Updates, Failure Recovery) are explicitly distinguished from strictly linear stages.
- [ ] The relationship to [45_Data_Lifecycle.md](45_Data_Lifecycle.md)'s Document Lifecycle is explicit — this document governs the connector instance, not the individual documents it produces.
