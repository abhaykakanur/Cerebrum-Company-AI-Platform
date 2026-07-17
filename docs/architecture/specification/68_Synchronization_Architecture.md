# 68 — Synchronization Architecture

## Purpose

This document defines the Synchronization Engine's architecture in full: the seven supported synchronization modes, the eight categories of change the Delta Detection Engine must identify, the ten fields every connector exposes for health monitoring, the Retry Engine's failure-handling strategy, and the Permission Synchronization Engine's scope. It elaborates FR-CN-003 through FR-CN-010 from [20_Functional_Requirements.md](20_Functional_Requirements.md) at implementation-informing depth.

## Scope

This document covers synchronization mechanics, health, retry, and permission sync. It does not cover metadata field extraction content (see [69_Metadata_Extraction.md](69_Metadata_Extraction.md)) or the connector lifecycle stages these mechanisms operate within (see [67_Connector_Lifecycle.md](67_Connector_Lifecycle.md)).

## Definitions

- **Synchronization Mode** — A distinct triggering and execution pattern for moving content from a source system into Cerebrum.
- **Delta** — The set of changes (additions, modifications, deletions, moves) between two sync states.
- **Circuit Breaker** — A failure-handling pattern that stops attempting an operation known to be currently failing, resuming attempts only after a cool-down period, preventing wasted retries against a definitively unavailable dependency.

## Synchronization Modes

The Synchronization Engine SHALL support the following seven modes, which are not mutually exclusive — a single Connector Instance typically uses several in combination over its lifecycle (per [67_Connector_Lifecycle.md](67_Connector_Lifecycle.md)):

| Mode | Description | Typical Use |
|---|---|---|
| Manual Synchronization | Explicitly triggered by an authorized actor. | Ad hoc refresh, initial testing, FR-CN-005's manual trigger. |
| Scheduled Synchronization | Triggered on a configured recurring interval. | Steady-state operation, FR-CN-005. |
| Incremental Synchronization | Processes only changed content since the last successful sync. | The default steady-state execution shape, FR-CN-004. |
| Real-time Webhook Synchronization | Triggered by an inbound push notification from the source system. | Low-latency freshness for sources supporting webhooks (per [65_Connector_Architecture.md](65_Connector_Architecture.md)'s Webhook Handler component). |
| Delta Synchronization | A synchronization run scoped explicitly to a known delta (e.g., reprocessing a specific set of changed item IDs received via webhook). | Fine-grained reconciliation, often invoked by Real-time Webhook Synchronization rather than run standalone. |
| Full Synchronization | Processes all in-scope content regardless of prior sync state. | Initial sync (FR-CN-003), recovery from a corrupted incremental state. |
| Hybrid Synchronization | Combines Scheduled Synchronization (as a freshness backstop) with Real-time Webhook Synchronization (for low-latency updates), so a missed or failed webhook does not permanently desynchronize the connector. | The recommended default operating mode for any source system supporting webhooks, since it does not rely solely on webhook delivery reliability. |

## Delta Detection

The Delta Detection Engine SHALL detect the following eight categories of change between sync states:

| Change Category | Detection Basis |
|---|---|
| New documents | Absent from the prior sync's known-item set. |
| Updated documents | Present in both sync states with a changed content hash or modification timestamp. |
| Deleted documents | Present in the prior sync's known-item set, absent from the current source-system enumeration. |
| Permission changes | Detected by the Permission Synchronization Engine (see below), independent of content changes — a document's content may be unchanged while its access control changed. |
| Metadata changes | A structural field (per [69_Metadata_Extraction.md](69_Metadata_Extraction.md)) changed without the content itself changing (e.g., a re-tag). |
| Relationship changes | A source-system-native relationship changed (e.g., a Jira issue's parent-epic link), feeding Knowledge Graph updates (FR-KG-002). |
| Folder movement | An item's location within the source system's organizational structure changed, without necessarily changing its content — updates Document Management's Collections/Folders (FR-DM-005) rather than triggering full reprocessing. |
| Renaming | An item's title/filename changed — a metadata change specifically called out given its high frequency and low reprocessing cost relative to a full content re-sync. |

Each category maps to a distinct handling path in the Knowledge Ingestion pipeline ([45_Data_Lifecycle.md](45_Data_Lifecycle.md)) — a Renaming or Folder Movement delta, for instance, need not re-trigger Text Extraction, OCR, or Embedding Generation, only a metadata update, directly supporting Scalability by avoiding unnecessary reprocessing.

## Connector Health

Every connector SHALL expose the following ten fields, extending FR-CN-006's health-status requirement with the complete field set:

| Field | Purpose |
|---|---|
| Health Status | The aggregate status (Healthy/Degraded/Failed, per FR-CN-006). |
| Last Sync Time | When the most recent sync run completed (successfully or not). |
| Current Sync | Whether a sync is actively in progress, and its stage (feeds FR-MN-002's progress requirement). |
| Last Failure | The most recent failure's timestamp and classification (see Retry Strategy below). |
| Error Count | Cumulative or windowed error count, for trend analysis (FR-AL-004). |
| Retry Count | Current retry attempt count for an in-progress recovery, per the Retry Engine below. |
| Latency | Observed sync operation latency, feeding [39_Performance_Targets.md](39_Performance_Targets.md)'s Connector Sync Reliability target. |
| Throughput | Items processed per unit time, informing capacity planning. |
| Document Count | Total items currently synced from this connector, informing Knowledge Coverage (FR-AL-003). |
| Permission Status | Whether the last Permission Synchronization Engine pass completed successfully — a distinct health signal from general sync health, since a connector can be content-healthy while permission-desynchronized. |

## Retry Strategy

The Retry Engine SHALL support the following six capabilities, extending FR-CN-007:

| Capability | Description |
|---|---|
| Exponential Backoff | Increasing delay between retry attempts, per [36_Background_Processing.md](36_Background_Processing.md)'s general retry pattern applied to connector sync specifically. |
| Retry Limits | A maximum attempt count before a failure is escalated rather than retried indefinitely. |
| Circuit Breaker | See definition above — prevents a definitively unavailable source system from consuming retry budget indefinitely; the circuit "opens" after a threshold of consecutive failures and "closes" (resumes attempts) after a cool-down period. |
| Failure Classification | Transient vs. non-transient, per [38_Observability.md](38_Observability.md)'s error taxonomy applied to the Connector Error category. |
| Dead Letter Queue Readiness | Per [36_Background_Processing.md](36_Background_Processing.md)'s DLQ pattern, scoped to failed sync items specifically. |
| Retry Scheduling | Retries are scheduled through the Background Processing Layer ([36_Background_Processing.md](36_Background_Processing.md)), not executed inline, so a retry storm across many connectors does not starve other background work. |

## Permission Synchronization

**Binding rule:** Search SHALL NEVER bypass source permissions. This is the Connector Domain's specific contribution to the platform-wide permission correctness guarantee already established across FR-AUTZ-003, FR-ES-010, and [46_Multi_Tenancy.md](46_Multi_Tenancy.md) — permission synchronization is what makes source-fidelity possible in the first place; without it, Cerebrum would have no accurate record of a source system's access control to enforce.

The Permission Synchronization Engine SHALL synchronize the following nine elements:

| Element | Purpose |
|---|---|
| Users | Source-system user identities, mapped to Cerebrum User accounts where a confident match exists (per Open Question 1 in [11_Open_Questions.md](11_Open_Questions.md)'s connector-identity-resolution territory). |
| Groups | Source-system group memberships, feeding permission inheritance. |
| Roles | Source-system role assignments, where the source system models roles distinctly from groups. |
| ACLs | Explicit access control list entries at the item level. |
| Ownership | The source-system-native owner of an item, feeding FR-ED-004's Knowledge Ownership Attribution. |
| Inherited Permissions | Permissions an item receives from its containing folder/space rather than an explicit grant, mirroring [35_Domain_Architecture.md](35_Domain_Architecture.md)'s Authorization Domain inheritance pattern at the source-system level. |
| Workspace Visibility | Whether an item is scoped to a specific source-system workspace/space/team, mapped to the corresponding Cerebrum Workspace scope. |
| Deleted Users | A source-system user's deletion/deprovisioning is synchronized so their prior access grants are correctly revoked in Cerebrum's mirrored permission state, not left stale. |
| Permission Changes | Detected as a Delta Detection category (above) and propagated promptly — a permission *tightening* at the source (access removed) SHALL propagate with priority over a permission *widening* (access added), since the former is the security-sensitive direction where delay creates risk, while the latter's delay only causes a temporary, safe under-grant. |

This synchronized permission state is what the Authorization Layer's `checkPermission`/`filterByPermission` ([35_Domain_Architecture.md](35_Domain_Architecture.md)) ultimately evaluates against for connector-sourced content — the Connector Domain populates the permission data; the Authorization Domain enforces it. Neither substitutes for the other.

## Responsibilities

- Every Connector Plugin must report Permission Changes with the asymmetric priority stated above (tightening before widening) — a plugin that treats both with equal priority is a security-relevant defect, not a minor inefficiency.
- The Circuit Breaker's threshold and cool-down parameters must be tuned per connector category where source systems have materially different failure/recovery profiles (Deferred to Architecture for specific values).

## Constraints

- This document does not specify exact backoff multipliers, circuit-breaker thresholds, or DLQ retention — Deferred to Architecture, consistent with Open Question 44 in [40_Open_Questions.md](40_Open_Questions.md).
- Permission synchronization accuracy depends on the source system's own API exposing sufficient permission detail — a source system with limited permission-API granularity (Deferred to Architecture, per-connector) may only support coarser-grained synchronization than this document's full nine-element list, which must be documented as a per-connector limitation, not silently assumed away.

## Future Considerations

- As Permission Synchronization accuracy is measured in production (extending FR-AL-004's Connector Analytics with a permission-sync-specific accuracy metric), connectors with weaker source-system permission APIs should be flagged for administrators as carrying elevated permission-drift risk.

## Acceptance Criteria

- [ ] All seven synchronization modes from the governing specification are defined.
- [ ] All eight delta detection categories from the governing specification are defined with their handling implication.
- [ ] All ten connector health fields from the governing specification are defined.
- [ ] All six retry strategy capabilities from the governing specification are defined.
- [ ] All nine permission synchronization elements from the governing specification are defined, with the "search shall never bypass source permissions" rule stated as binding and connected to the Authorization Domain.
