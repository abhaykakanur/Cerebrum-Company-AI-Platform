# 101 — Monitoring Architecture

## Purpose

This document defines the twelve categories of infrastructure/application metrics Cerebrum collects, the ten health check types every service exposes, and the Logging Standards governing every log entry platform-wide. It elaborates [38_Observability.md](38_Observability.md) (Part 3) with the concrete, enumerated metric and health-check lists that document's abstract architecture assumed but did not itemize.

## Scope

This document covers monitoring metrics, health check types, and logging field requirements. It does not redefine the observability *architecture* (structured logging mechanism, tracing propagation, error taxonomy) — see [38_Observability.md](38_Observability.md) for that.

## Definitions

See [10_Glossary.md](10_Glossary.md) and [38_Observability.md](38_Observability.md). No new terms are introduced here.

## Monitoring

Collect: CPU, Memory, Disk, Network, Queue Depth, Job Latency, API Latency, Database Latency, Search Latency, LLM Latency, Connector Latency, Worker Health.

| Metric | Category | Feeds |
|---|---|---|
| CPU, Memory, Disk, Network | Infrastructure-level resource metrics | Capacity planning, [39_Performance_Targets.md](39_Performance_Targets.md)'s Horizontal Scaling triggers. |
| Queue Depth | Background Processing Layer | [92_Queue_Architecture.md](92_Queue_Architecture.md)'s Monitoring Queue Feature, [88_Dashboard_Architecture.md](88_Dashboard_Architecture.md)'s Jobs Queue Status widget. |
| Job Latency | Background Processing Layer | [92_Queue_Architecture.md](92_Queue_Architecture.md)'s Job Record Duration field, aggregated. |
| API Latency | API Domain | [81_API_Standards.md](81_API_Standards.md)'s Observability Latency metric. |
| Database Latency | Persistence Layer | Per-datastore ([42_Database_Responsibilities.md](42_Database_Responsibilities.md)) query performance. |
| Search Latency | Enterprise Search Domain | Directly measured against the Search Response performance target ([39_Performance_Targets.md](39_Performance_Targets.md)). |
| LLM Latency | AI Layer | Directly measured against the Time to First Token and Average AI Response targets ([51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md)). |
| Connector Latency | Connector Domain | [68_Synchronization_Architecture.md](68_Synchronization_Architecture.md)'s Connector Health Latency field, aggregated platform-wide. |
| Worker Health | Background Processing Layer | [91_Background_Processing.md](91_Background_Processing.md)'s per-Worker health status. |

This list is the concrete instantiation of [38_Observability.md](38_Observability.md)'s Metrics architecture (Counters/Gauges/Histograms) — every metric above is implemented as one of those three primitive types via the shared Prometheus-compatible instrumentation port already established there.

## Health Checks

Expose: Liveness, Readiness, Startup, Dependency Health, Database Health, Vector DB Health, Graph DB Health, Cache Health, Object Storage Health, LLM Provider Health.

| Check | Relationship to [38_Observability.md](38_Observability.md)'s Three Check Types |
|---|---|
| Liveness | Directly corresponds to that document's Liveness check. |
| Readiness | Directly corresponds to that document's Readiness check. |
| Startup | A new, distinct third phase — confirms a service has completed its initialization sequence (e.g., warming caches, establishing initial datastore connections) before it is even eligible to be evaluated for Readiness; prevents a slow-starting instance from being prematurely marked unready-but-polled-anyway, distinguishing "still starting up" from "started but temporarily unhealthy." |
| Dependency Health | The aggregate rollup of every check below it in this list — corresponds to [38_Observability.md](38_Observability.md)'s "detailed Health check." |
| Database Health, Vector DB Health, Graph DB Health, Cache Health, Object Storage Health | Per-datastore health, one check per [42_Database_Responsibilities.md](42_Database_Responsibilities.md)'s five datastores (PostgreSQL, Qdrant, Neo4j, Redis, MinIO respectively). |
| LLM Provider Health | Per [60_AI_Model_Abstraction.md](60_AI_Model_Abstraction.md)'s active provider(s) — confirms the configured Default and Fallback Models ([62_AI_Governance.md](62_AI_Governance.md)) are currently reachable. |

The addition of a formal Startup check (beyond [38_Observability.md](38_Observability.md)'s original Liveness/Readiness/detailed-Health three-way split) is this document's specific refinement — Startup is a sub-case of Readiness in that document's original framing, elevated here to its own named check given its operational importance for services with non-trivial initialization (notably any service establishing connections to all five datastores at boot).

## Logging Standards

**Use structured logging.** Every log SHALL include: Timestamp, Correlation ID, Tenant ID, Workspace ID, Request ID, Component, Severity, Message, Context.

This is the complete, itemized field list for [38_Observability.md](38_Observability.md)'s Structured Logging architecture, which required "timestamp, log level, originating domain/component, and a correlation identifier" at minimum — this document adds Tenant ID and Workspace ID (per [46_Multi_Tenancy.md](46_Multi_Tenancy.md)'s scoping, essential for any log query to be tenant-filterable) and Request ID (distinct from Correlation ID per [81_API_Standards.md](81_API_Standards.md)'s definitions) as explicitly required fields, and renames "log level" to "Severity" and "originating domain/component" to "Component" for consistency with this document's terminology.

**Binding rule:** Sensitive data SHALL NEVER be logged. This restates [38_Observability.md](38_Observability.md)'s field-redaction requirement and [75_Security_Architecture.md](75_Security_Architecture.md)'s Token Strategy Secure Storage rule as a single, platform-wide logging commandment — the "Context" field specifically is the highest-risk field for accidental sensitive-data inclusion (since it is often populated with whatever local variables seem relevant at the log call site) and therefore requires the strictest redaction-ruleset enforcement of any field in this list.

### Decision Rationale: Why Structured Logging

Structured logging is mandated, rather than free-text logging, because it is the only format that makes the nine required fields above reliably queryable at scale — a free-text log message might contain a Tenant ID as a substring, but only structured logging guarantees it as a distinct, indexed, filterable field. This is a direct precondition for [47_Data_Governance.md](47_Data_Governance.md)'s Audit Domain requirement that records be "queryable by resource, actor, and time range," and for [46_Multi_Tenancy.md](46_Multi_Tenancy.md)'s requirement that operational tooling never accidentally surface one tenant's logs when investigating another's issue.

## Responsibilities

- Every new service or Worker introduced in a later phase must expose all applicable Health Checks from this list before being considered production-ready — a service with only a Liveness check but no Readiness/Startup distinction risks receiving traffic before it can correctly serve it.
- The sensitive-data-never-logged rule must be enforced via the same automated redaction mechanism as [38_Observability.md](38_Observability.md) established, verified in Security Testing ([98_Testing_Strategy.md](98_Testing_Strategy.md)) via Secret Detection scanning of log output specifically, not only source code.

## Constraints

- This document does not specify metric collection intervals, retention periods, or alerting thresholds — Deferred to Architecture/operations, per Open Question 50 in [40_Open_Questions.md](40_Open_Questions.md).
- This document does not specify the exact Startup check's completion criteria per service — Deferred to Architecture, per-service.

## Future Considerations

- As new datastores or external dependencies are added (per [12_Future_Expansion.md](12_Future_Expansion.md)), a corresponding Health Check must be added to this list, maintaining Dependency Health's completeness as a true aggregate of every external dependency, not a stale subset.

## Acceptance Criteria

- [ ] All twelve Monitoring metrics from the governing specification are defined with their feeding purpose.
- [ ] All ten Health Check types from the governing specification are defined, with the new Startup check's relationship to [38_Observability.md](38_Observability.md)'s original three-type model made explicit.
- [ ] All nine Logging Standards fields from the governing specification are defined, with the sensitive-data rule stated as binding and the Structured Logging Decision Rationale included.
