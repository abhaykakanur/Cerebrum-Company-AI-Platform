# 39 — Performance Targets and Scalability Strategy

## Purpose

This document defines Cerebrum's target performance metrics and the architectural strategy for scaling to meet them at enterprise volume (thousands of organizations, millions of documents, per [01_Product_Vision.md](01_Product_Vision.md)). It elaborates the request-path latency assumptions referenced throughout [30_System_Architecture.md](30_System_Architecture.md) and [31_Component_Architecture.md](31_Component_Architecture.md).

## Scope

This document covers target metrics and scaling strategy at the architecture level. It does not commit to specific infrastructure sizing, instance counts, or cloud-provider capacity plans — Deferred to Architecture-time operational planning informed by real usage data.

## Definitions

- **First Token Latency** — Time from a chat query being submitted to the first token of the AI-generated answer being delivered to the client, distinct from full-answer completion time.
- **Horizontal Scaling** — Increasing capacity by adding more instances of a stateless component, as opposed to increasing a single instance's resources (vertical scaling).
- **Read Replica** — A read-only copy of a datastore kept in sync with a primary, used to distribute read load.

## Performance Targets

| Metric | Target | Rationale |
|---|---|---|
| Search Response | < 2 seconds | Directly operationalizes the Search Latency metric category in [08_Success_Metrics.md](08_Success_Metrics.md); anchors the "reduce search time" goal in [02_Project_Goals.md](02_Project_Goals.md). |
| Knowledge Retrieval (Retrieval Domain context assembly) | < 1 second | Retrieval must complete well within the Chat Response First Token budget below, since AI Reasoning cannot begin generation until context assembly completes. |
| Chat Response First Token | < 3 seconds | Perceived responsiveness for a conversational interface; informed by the streaming architecture in [31_Component_Architecture.md](31_Component_Architecture.md), which allows generation to begin streaming before the full answer, citations, and confidence score are finalized. |
| Connector Sync Reliability | > 99% | Directly operationalizes the Connector Reliability metric category; a sync's success rate (excluding source-system outages outside Cerebrum's control) must remain above this threshold on a rolling basis. |
| System Availability | > 99.9% | Directly operationalizes the System Uptime metric category; corresponds to no more than roughly 8.7 hours of unplanned downtime per year. |

These targets are Version 1.0 architectural design goals, not contractual SLAs — a specific customer-facing SLA commitment is a business decision outside this specification's scope, tracked as Open Question 11 (compliance/regulatory scope) in [11_Open_Questions.md](11_Open_Questions.md) territory.

## Target Traceability

| Target | Primarily Constrained By | Key Architectural Levers |
|---|---|---|
| Search Response | Enterprise Search Domain, Authorization Layer permission filtering | OpenSearch query performance, Authorization Layer call latency (see [31_Component_Architecture.md](31_Component_Architecture.md) performance note), result-set caching. |
| Knowledge Retrieval | Retrieval Domain, Knowledge Graph Domain traversal | Qdrant/OpenSearch/Neo4j query parallelization, token-budgeting truncation avoiding oversized context assembly. |
| Chat Response First Token | AI Layer, LLM Provider latency | Streaming response architecture, provider selection/fallback, prompt/context size discipline (FR-RT-005 token budgeting). |
| Connector Sync Reliability | Connector Layer, Background Processing Layer | Retry policy ([36_Background_Processing.md](36_Background_Processing.md)), per-connector circuit breaking to avoid cascading failure from one degraded source system. |
| System Availability | All fifteen components | Horizontal scaling, health-check-driven traffic routing ([38_Observability.md](38_Observability.md)), graceful degradation (e.g., Search Error handling falling back from hybrid to keyword-only). |

## Scalability Strategy

### Horizontal Scaling

The Backend Layer (modular monolith) SHALL be deployed as multiple stateless process instances behind a load balancer. Statelessness is achieved by keeping all session state in Redis (not in-process memory) and all durable state in the Persistence Layer, per the Kubernetes-Ready deployment target in [32_Technology_Stack.md](32_Technology_Stack.md). Horizontal scaling of the Backend Layer directly addresses the System Availability target by allowing rolling deployments and instance failure without full-system downtime.

### Read Replicas

PostgreSQL SHALL support read replicas for read-heavy, latency-tolerant query paths (e.g., Analytics Layer reporting, Audit Domain history queries) so they do not contend with the primary's write-path capacity needed for Identity, Workspace, Authorization, and Configuration domains' transactional correctness.

### Caching

The Configuration Layer's aggressive Redis caching (per [37_Configuration_Strategy.md](37_Configuration_Strategy.md)) and Authorization Layer's permission-decision caching (Deferred to Architecture for cache-invalidation mechanics, given the correctness sensitivity flagged in [31_Component_Architecture.md](31_Component_Architecture.md)) are the two highest-leverage caching points, since both are called on nearly every request.

### Queue Scaling

The Background Processing Layer's worker pool SHALL scale independently of the Backend Layer's request-serving instances, since ingestion/processing load (bursty, driven by connector sync volume) has a different scaling profile than request-serving load (driven by concurrent user activity). Per-Task-category worker pools (see [36_Background_Processing.md](36_Background_Processing.md)) allow, for example, scaling embedding-generation workers independently of connector-sync workers if one becomes a bottleneck.

### Search Scaling

OpenSearch SHALL scale via its native sharding and replica mechanisms, with shard count planned around projected document volume per tenant/organization rather than a single global index whose growth is unbounded — the specific sharding strategy (e.g., index-per-organization vs. shared index with tenant-filtered queries) is Deferred to Architecture, directly tied to the multi-tenancy model decision in Open Question 3 of [11_Open_Questions.md](11_Open_Questions.md).

### Vector Scaling

Qdrant SHALL scale via its native clustering support as embedding volume grows with document count; embedding dimensionality and collection partitioning strategy (per-organization vs. shared, filtered) follow the same tenancy-model dependency as Search Scaling above.

### Graph Scaling

Neo4j SHALL scale via read replicas for traversal-heavy query load (FR-KG-006) and, if write volume from entity/relationship extraction becomes a bottleneck, via write-path batching in the Background Processing Layer's graph-extraction Task rather than issuing one write per extracted entity/relationship.

## Responsibilities

- Any component whose observed performance falls outside its target in production must trigger an architecture review, not a silent target revision — targets are revised only through the governance process in [09_Governance.md](09_Governance.md), informed by real data.
- Capacity planning based on this strategy is an operations-phase responsibility building on, not replacing, the architectural levers named here.

## Constraints

- No specific instance count, CPU/memory sizing, or cloud spend figure is specified in this document — those are operational planning decisions made against real usage data, not Phase 0 architecture decisions.
- The performance targets in this document are Version 1.0 design goals; they are not a substitute for a customer-facing SLA, which is a business/legal decision outside this specification.

## Future Considerations

- As usage data accumulates post-launch, the Scalability Strategy's per-store scaling approaches (sharding strategy, replica counts) should be revisited against actual load patterns rather than the projections implicit in this document.
- The tenancy-model decision (Open Question 3) materially affects Search, Vector, and Graph Scaling strategy and should be prioritized early in the architecture-implementation phase given its downstream impact on three separate scaling strategies.

## Acceptance Criteria

- [ ] All five performance targets named in the governing specification are stated with a clear rationale.
- [ ] Each target is traced to the architectural components that primarily constrain it.
- [ ] All seven scalability strategy areas named in the governing specification (horizontal scaling, read replicas, caching, queue scaling, search scaling, vector scaling, graph scaling) are addressed.
