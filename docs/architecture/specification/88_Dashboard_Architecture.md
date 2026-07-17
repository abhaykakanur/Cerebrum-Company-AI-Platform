# 88 — Dashboard Architecture

## Purpose

This document defines the Dashboard's twelve widget categories and maps each to its backend data source, ensuring the Dashboard is a thin presentation layer over existing Analytics, Monitoring, and Connector Health capability — not a source of new backend logic.

## Scope

This document covers Dashboard widget composition and data sourcing. It does not cover the underlying Analytics/Monitoring architecture (see [35_Domain_Architecture.md](35_Domain_Architecture.md), [38_Observability.md](38_Observability.md), [61_AI_Evaluation.md](61_AI_Evaluation.md), [73_Search_Analytics.md](73_Search_Analytics.md)) or the Chart/Data Grid components rendering this data (see [87_Component_Library.md](87_Component_Library.md)).

## Definitions

- **Widget** — A self-contained Dashboard panel presenting one category of aggregated information, composed from Design System components ([87_Component_Library.md](87_Component_Library.md)) per the Thin Frontend rule ([85_Frontend_Architecture.md](85_Frontend_Architecture.md)).

## Dashboard Widgets

| Widget | Backend Data Source |
|---|---|
| Knowledge KPIs | Analytics Domain's Knowledge Coverage Analytics (FR-AL-003), [08_Success_Metrics.md](08_Success_Metrics.md)'s Knowledge Coverage metric category. |
| Connector Health | [68_Synchronization_Architecture.md](68_Synchronization_Architecture.md)'s ten Connector Health fields, via Connector Analytics (FR-AL-004). |
| Recent Documents | Knowledge Storage Domain, filtered by recency per the requesting user's permission-scoped access (FR-AUTZ-003). |
| Recent Conversations | Conversation Domain's Conversation History (FR-CV-003), scoped to the requesting user. |
| Search Analytics | [73_Search_Analytics.md](73_Search_Analytics.md)'s eight tracked metrics. |
| AI Usage | [61_AI_Evaluation.md](61_AI_Evaluation.md)'s telemetry, aggregated (request volume, active users per Usage Analytics FR-AL-002). |
| Token Usage | [61_AI_Evaluation.md](61_AI_Evaluation.md)'s Token Usage evaluation metric, aggregated over the dashboard's time window. |
| Latency | [39_Performance_Targets.md](39_Performance_Targets.md) and [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md)'s stage-level Performance Targets, presented as observed-vs-target. |
| Knowledge Growth | Analytics Domain, tracking indexed content volume over time (an extension of FR-AL-003's coverage tracking with a temporal dimension). |
| Trending Topics | [73_Search_Analytics.md](73_Search_Analytics.md)'s Popular Topics metric. |
| Jobs Queue Status | [92_Queue_Architecture.md](92_Queue_Architecture.md)'s Job Lifecycle state distribution (how many jobs are Queued/Executing/Retry/Completed/Archived). |
| System Health | [38_Observability.md](38_Observability.md)'s Health Check architecture (FR-MN-001, FR-MN-004's Uptime Dashboard — this widget is the Dashboard's realization of that requirement's UI surface). |

## Permission-Scoped Composition

Every widget's data is filtered by the requesting user's Authorization Layer permissions before reaching the Dashboard ([77_Authorization_Model.md](77_Authorization_Model.md)) — a Workspace Administrator sees connector-wide health for their workspace; an Employee-role user sees only their own Recent Documents and Recent Conversations, never another user's, consistent with the same permission-scoping rule applied everywhere else in this specification. System Health and Connector Health widgets are visible only to roles carrying Administration or Connector management permissions per [78_RBAC_Model.md](78_RBAC_Model.md)'s role catalog, not to every user by default.

## Responsibilities

- Every Dashboard widget must source its data through the API Domain's existing Public/Administrative API surfaces ([80_API_Architecture.md](80_API_Architecture.md)) — the Dashboard introduces no new backend aggregation logic of its own; if a widget requires an aggregation the backend does not yet expose, that aggregation belongs in the Analytics Domain, not computed client-side.
- The Dashboard's < 2 second Performance Target ([85_Frontend_Architecture.md](85_Frontend_Architecture.md)) must be met with all twelve widgets loaded — widget-level lazy-loading and Skeleton Loader states ([87_Component_Library.md](87_Component_Library.md)) are the primary mechanism for meeting this target without blocking on the slowest widget's data source.

## Constraints

- This document does not specify widget layout, sizing, or arrangement — a Frontend Layer visual-design concern Deferred to Architecture.
- This document does not introduce new Analytics Domain metrics beyond what Parts 2–7 already define — every widget maps to existing, already-specified data.

## Future Considerations

- As Dashboard usage is observed, widget relevance and default arrangement should be informed by actual engagement data, potentially supporting user-customizable widget selection/arrangement as a future enhancement beyond this Version 1.0 fixed twelve-widget set.

## Acceptance Criteria

- [ ] All twelve Dashboard widgets from the governing specification are defined with a traced backend data source.
- [ ] Permission-scoped composition is explicitly addressed — no widget is assumed universally visible regardless of role.
- [ ] The Dashboard is confirmed as introducing no new backend aggregation logic, consistent with the Thin Frontend principle.
