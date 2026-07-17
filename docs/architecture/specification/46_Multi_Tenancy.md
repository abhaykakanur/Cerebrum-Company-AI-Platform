# 46 — Multi-Tenancy

## Purpose

This document defines Cerebrum's tenant isolation architecture: how every datastore enforces that no record, node, vector, or cache entry is ever accessible across tenant boundaries. It resolves Open Questions 38 (PostgreSQL multi-tenancy isolation model) and 41 (search/vector index partitioning) from [40_Open_Questions.md](40_Open_Questions.md) with binding architectural decisions.

## Scope

This document covers tenant isolation mechanics per datastore. It does not cover the Authorization Domain's user-level, resource-scoped permission model (see [35_Domain_Architecture.md](35_Domain_Architecture.md)'s Authorization Domain entry) — tenant isolation is the outer boundary (no organization ever sees another organization's data under any circumstance); Authorization is the inner boundary (within one organization, which specific users/roles see which resources). Both are required; neither substitutes for the other.

## Definitions

- **Tenant** — An Organization, the unit of isolation; every record belongs to exactly one Tenant.
- **Row-Level Security (RLS)** — A PostgreSQL feature enforcing row visibility filters at the database engine level, independent of and in addition to application-level query filtering.
- **Noisy Neighbor** — A multi-tenancy failure mode where one tenant's load degrades performance for others sharing the same infrastructure.

## Resolution of Prior Open Questions

This document makes the following binding decisions, closing Open Questions 38 and 41 from [40_Open_Questions.md](40_Open_Questions.md). A future implementation phase should record the corresponding ADR per [09_Governance.md](09_Governance.md) and mark those rows resolved.

- **Open Question 38 (PostgreSQL isolation model):** Resolved as **shared schema with a mandatory `tenant_id` column on every table, enforced by PostgreSQL Row-Level Security policies** — not schema-per-tenant, not database-per-tenant. Rationale below.
- **Open Question 41 (search/vector partitioning):** Resolved as **shared index/collection with mandatory tenant-filtered queries**, with **dedicated per-tenant collections/indexes as an escape hatch for the largest enterprise tenants** once justified by observed scale. Rationale below.

## PostgreSQL Tenant Isolation

**Decision:** Every table SHALL carry a `tenant_id` column, and every table SHALL have a PostgreSQL Row-Level Security policy restricting all `SELECT`/`INSERT`/`UPDATE`/`DELETE` operations to rows matching the currently authenticated session's `tenant_id`.

**Rationale:** Schema-per-tenant or database-per-tenant does not scale operationally to "thousands of organizations" per [01_Product_Vision.md](01_Product_Vision.md) — running and migrating thousands of schemas or databases is an operational burden disproportionate to the isolation benefit. A shared schema with RLS gives isolation enforced at the database engine level (defense in depth beyond application-level `WHERE tenant_id = ?` filtering, which is only as reliable as every single query author remembering to include it) while remaining operable at scale with a single schema to migrate and maintain.

**Enforcement mechanism:** Every database connection used by an authenticated request sets a session-local `app.current_tenant_id` variable (via `SET LOCAL`, scoped to the transaction) immediately after establishing the connection and before any query executes; every table's RLS policy checks incoming rows against this variable. A connection that fails to set this variable is denied access to any tenant-scoped table by default (fail-closed, not fail-open), satisfying Security by Default from [04_Project_Principles.md](04_Project_Principles.md).

**No cross-tenant joins:** Because RLS is enforced per-table regardless of query shape, a query that attempts to join across two tables would still have each table's rows independently filtered to the session's tenant — making an accidental cross-tenant join return zero rows for the mismatched side rather than leaking data, not merely a "shall not" convention.

## Neo4j Tenant Isolation

**Decision:** Every node and relationship SHALL carry a `tenant_id` property. Every Cypher query issued by the Knowledge Graph Domain's repository adapter SHALL include a mandatory `tenant_id` predicate, enforced at the query-construction layer (the adapter refuses to build or execute a query missing this predicate) rather than relying on Neo4j engine-level enforcement, since Neo4j (Community/default configuration) does not offer RLS-equivalent native enforcement.

**No cross-tenant graph traversal:** The query-construction layer's mandatory predicate applies to traversal depth as well as the starting node — a traversal SHALL NOT be permitted to cross a relationship into a node belonging to a different `tenant_id`, even transitively, enforced by filtering traversal results post-query if the underlying Cypher pattern cannot exclude it pre-query (Deferred to Architecture for the specific Cypher pattern).

**Escape hatch for scale:** For the largest enterprise tenants (volume threshold Deferred to Architecture), a dedicated Neo4j database (using Neo4j's native multi-database capability) MAY be provisioned, moving that tenant's isolation guarantee from query-layer enforcement to physical database separation. This is an operational scaling decision, not a change to the logical data model in [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md).

## Qdrant Tenant Isolation

**Decision:** Every vector's payload SHALL carry an indexed `tenant_id` field. Every Retrieval Domain and Enterprise Search Domain query against Qdrant SHALL include a mandatory payload filter on `tenant_id`, enforced at the same query-construction layer pattern as Neo4j above.

**No cross-tenant vector retrieval:** Qdrant's payload-filtering is applied *before* the approximate-nearest-neighbor search executes (pre-filtering), not after (post-filtering a top-K result set), preventing the failure mode where a tenant's legitimate top-K results are silently displaced by another tenant's higher-scoring, but inaccessible, vectors.

**Escape hatch for scale:** As with Neo4j, the largest enterprise tenants MAY be provisioned a dedicated Qdrant collection once payload-filtered query performance on the shared collection no longer meets the Knowledge Retrieval performance target in [39_Performance_Targets.md](39_Performance_Targets.md), at which point the tenant's writes are routed to its dedicated collection transparently to the Knowledge Processing Domain (an Infrastructure Layer routing decision, not a domain-layer change, per Dependency Inversion in [34_Architecture_Principles.md](34_Architecture_Principles.md)).

## Redis Tenant Isolation

**Decision:** Every cache key SHALL be namespaced with the `tenant_id` as a mandatory key-prefix segment (e.g., `{tenant_id}:config:{key}`, `{tenant_id}:session:{session_id}`). This is enforced by the shared Redis-adapter helper that every domain's cache/session/lock usage goes through (per [37_Configuration_Strategy.md](37_Configuration_Strategy.md)) — no domain constructs a raw Redis key without this helper.

**Noisy-neighbor consideration:** Because Redis is shared infrastructure without per-key access control, tenant-prefixing prevents *data* leakage but not *performance* leakage (one tenant's high cache-churn workload can still evict another tenant's cache entries). Per-tenant Redis resource quotas or a dedicated Redis instance for the largest tenants are a scaling lever, tracked as a future consideration below, not a V1.0 requirement.

## MinIO Tenant Isolation

**Decision:** Object keys SHALL be structured as `{tenant_id}/{workspace_id}/{entity_type}/{entity_id}/{filename}`, within a shared bucket (or a small, fixed set of buckets by environment/region), rather than one bucket per tenant.

**Rationale:** Most S3-compatible object storage services impose practical limits on bucket count per account (often in the low thousands), which "thousands of organizations" would approach or exceed; prefix-based partitioning has no such ceiling and is the standard pattern for multi-tenant object storage at this scale.

**Enforcement:** Every MinIO access is mediated by the Document Management and Knowledge Storage Domains' Infrastructure Layer adapter, which constructs the object key from the authenticated request's `tenant_id`/`workspace_id` and never accepts a caller-supplied full object key — preventing a path-traversal-style cross-tenant access attempt.

## Cross-Store Isolation Summary

| Datastore | Isolation Mechanism | Enforcement Point |
|---|---|---|
| PostgreSQL | `tenant_id` column + Row-Level Security | Database engine (fail-closed) |
| Neo4j | `tenant_id` property + mandatory query predicate | Query-construction layer (application) |
| Qdrant | `tenant_id` payload field + mandatory pre-filter | Query-construction layer (application) |
| Redis | `tenant_id` key-prefix namespacing | Shared cache-adapter helper (application) |
| MinIO | `tenant_id` object-key-prefix namespacing | Storage adapter (application), no caller-supplied raw keys |

Only PostgreSQL's isolation is enforced at the database engine level; the other four rely on disciplined, centralized application-layer enforcement. This is an explicit, accepted architectural risk — mitigated by the Global Forbidden Dependency rules in [35_Domain_Architecture.md](35_Domain_Architecture.md) ensuring no domain constructs a raw query against these stores outside their designated adapter, and by the security-testing verification called for in [30_System_Architecture.md](30_System_Architecture.md)'s Security Overview (FR-SC-004).

## Responsibilities

- Every new table, node label, vector collection, cache-key pattern, or object-key pattern introduced in a later phase must follow the isolation mechanism specified here for its datastore before it is considered production-ready.
- Security testing (per FR-SC-004) must specifically attempt cross-tenant access against every datastore, not only PostgreSQL, given the varying enforcement strength described above.

## Constraints

- This document does not specify the exact volume threshold that triggers a dedicated Neo4j database or Qdrant collection for a large tenant — Deferred to Architecture, to be set from observed production load.
- Workspace-level isolation *within* a tenant is Authorization Domain's responsibility (permission-scoped, not physically separated data), not this document's.

## Future Considerations

- Per-tenant Redis resource quotas or instance dedication, to address the noisy-neighbor gap noted above, should be evaluated once real multi-tenant load data exists.
- If a future customer segment requires physically dedicated infrastructure (not merely logical isolation) for regulatory reasons, this is the "dedicated single-tenant deployment option" named in [12_Future_Expansion.md](12_Future_Expansion.md), architecturally distinct from the escape-hatch scaling patterns described here.

## Acceptance Criteria

- [ ] Every datastore named in the governing specification's Tenant Isolation section has a concrete, enforced isolation mechanism, not merely a stated intention.
- [ ] "No cross-tenant joins," "no cross-tenant graph traversal," and "no cross-tenant vector retrieval" are each addressed with a specific enforcement mechanism.
- [ ] Open Questions 38 and 41 from [40_Open_Questions.md](40_Open_Questions.md) are explicitly resolved with a stated rationale.
