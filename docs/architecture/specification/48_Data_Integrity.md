# 48 — Data Integrity

## Purpose

This document defines the ten data integrity rules Cerebrum's architecture enforces, and — critically, given the polyglot persistence model in [41_Data_Architecture.md](41_Data_Architecture.md) — states *how* and *where* each rule is enforced when the entities involved span more than one datastore, since not every rule is natively enforceable by every technology in the stack.

## Scope

This document covers integrity enforcement mechanisms. It does not cover tenant isolation (a related but distinct integrity concern, see [46_Multi_Tenancy.md](46_Multi_Tenancy.md)) or governance policy (see [47_Data_Governance.md](47_Data_Governance.md)).

## Definitions

- **Referential Integrity** — The guarantee that a reference from one record to another always points to a record that actually exists.
- **Logical Foreign Key** — A reference between records in two different datastores, which cannot be enforced by either datastore's native constraint mechanism and must instead be enforced by write-ordering and integrity-sweep patterns.
- **Optimistic Locking** — A concurrency-control strategy where a write is accepted only if the record has not changed since it was read, detected via a version-number comparison, rather than via a held database lock.

## The Ten Integrity Rules

### 1. Foreign Keys

**Within PostgreSQL:** Every relationship between two PostgreSQL-owned entities (e.g., `Document.workspace_id → Workspace.id`) SHALL be enforced by a native PostgreSQL foreign key constraint, per the naming convention in [47_Data_Governance.md](47_Data_Governance.md).

**Across datastores:** A reference from a PostgreSQL row to a Neo4j node, Qdrant vector, or MinIO object (e.g., `Chunk.embedding_ref → Qdrant vector ID`) is a **Logical Foreign Key** — not enforceable by any native constraint. Integrity here is achieved by: (a) write-ordering — the PostgreSQL row referencing a not-yet-created secondary-store record is only created after that secondary-store write is confirmed, *or* is created first with the reference field null/pending until confirmation, per the pipeline stage gating in [45_Data_Lifecycle.md](45_Data_Lifecycle.md); and (b) periodic integrity sweeps (FR-KS-007) that detect and report logical-foreign-key violations (a `Chunk` row referencing a missing Qdrant vector) rather than assuming they cannot occur.

### 2. Unique Constraints

Enforced natively within PostgreSQL per entity (e.g., `uq_users_email` scoped within an organization, `uq_organizations_slug` globally). Uniqueness constraints that must hold across a tenant boundary are scoped by `tenant_id` as a composite unique constraint (e.g., unique on `(tenant_id, email)`, not `email` alone), consistent with [46_Multi_Tenancy.md](46_Multi_Tenancy.md).

### 3. Check Constraints

Enforced natively within PostgreSQL for enumerated fields (e.g., `Lifecycle State` must be one of the values defined in [45_Data_Lifecycle.md](45_Data_Lifecycle.md)'s universal state model or its category-specific extension) and for cross-field invariants expressible as a single-row check (e.g., `deleted_at IS NOT NULL` only when `deleted = true`).

### 4. Optimistic Locking

Enforced via the Base Entity Envelope's `Version` integer field ([44_Global_Entity_Model.md](44_Global_Entity_Model.md)): every update statement includes a `WHERE version = :expected_version` clause and increments `version` on success; a zero-row-affected result indicates a concurrent modification occurred, and the application layer SHALL surface this as a Validation Error (per [38_Observability.md](38_Observability.md)'s error taxonomy) requiring the caller to re-read and retry, never silently overwriting. This directly protects the aggregate-consistency guarantee described in [34_Architecture_Principles.md](34_Architecture_Principles.md)'s Domain Layer Architecture.

### 5. Transaction Boundaries

**Within PostgreSQL:** Every command handler (per [34_Architecture_Principles.md](34_Architecture_Principles.md)) executes within exactly one PostgreSQL transaction, committed atomically or rolled back entirely.

**Across datastores:** No transaction spans PostgreSQL and any secondary store — this is the direct consequence of [41_Data_Architecture.md](41_Data_Architecture.md)'s Strong vs. Eventual Consistency resolution. Cerebrum does NOT use two-phase commit or a distributed-transaction coordinator across heterogeneous stores. Instead, a **transactional outbox pattern** SHALL be used: the PostgreSQL transaction that creates or modifies an entity also writes an outbox record (within the same transaction, so it is atomic with the entity change) describing the secondary-store write that must eventually occur; a Background Processing Task polls/consumes the outbox and performs the secondary-store write, retrying until confirmed, then marks the outbox record complete. This guarantees at-least-once eventual propagation without ever requiring a distributed transaction.

### 6. Immutable IDs

The Base Entity Envelope's Internal UUID is assigned once at creation (via application-layer UUID generation before the first insert, not a database sequence) and is never reassigned, reused, or recycled — even after hard deletion via the Retention Sweep — preventing a deleted entity's identifier from ever being silently repurposed for an unrelated new entity, which would corrupt any Audit Event or Citation still referencing the old ID for historical purposes.

### 7. Immutable Audit History

The Audit Event entity category has no update or delete code path in any domain's application service — per [35_Domain_Architecture.md](35_Domain_Architecture.md)'s Audit Domain entry, "mutation methods on this entity are intentionally absent." This is enforced at the domain layer (no `UpdateAuditEvent`/`DeleteAuditEvent` use case exists to call) and reinforced at the PostgreSQL layer via a database-level restriction (e.g., a trigger rejecting `UPDATE`/`DELETE` on the `audit_events` table for all roles except the narrowly scoped retention-sweep role, itself subject to the retention policy's legal-hold check) — defense in depth, not reliance on application discipline alone.

### 8. No Orphan Records

**Within PostgreSQL:** Enforced via foreign key `ON DELETE` behavior (`CASCADE` for true compositional ownership like `Document → Chunk`, `RESTRICT` where deletion should be blocked pending explicit handling, e.g., a `Workspace` with active `Document`s per FR-WS-005's grace-period design).

**Across datastores:** A Document's hard deletion (per [47_Data_Governance.md](47_Data_Governance.md)'s Retention Sweep) SHALL only mark the PostgreSQL row fully purged after confirming removal of its Qdrant Embeddings, solely-derived Neo4j Knowledge Entities/Relationships, and MinIO binary — orchestrated as a multi-step Background Processing workflow (per [36_Background_Processing.md](36_Background_Processing.md)) with each step's completion tracked, so a partial failure leaves a detectable, resumable in-progress deletion rather than a silent orphan in a secondary store.

### 9. Relationship Validation

**Within Neo4j:** Since Neo4j does not natively enforce that a relationship's endpoints are of a permitted type pairing (e.g., preventing a `WORKS_ON` relationship between two `Person` nodes, which is semantically invalid), the Knowledge Graph Domain's application layer validates relationship-type/endpoint-type compatibility *before* issuing the Cypher write, per the Domain Layer's Business Rules pattern in [34_Architecture_Principles.md](34_Architecture_Principles.md) — invalid combinations are rejected as a Validation Error, never written and cleaned up later.

**Within PostgreSQL:** Standard foreign key constraints suffice, per rule 1.

### 10. Entity Validation

Every entity's domain-level invariants (e.g., FR-WS-003's "a workspace always has at least one active owner") are enforced by the entity's own mutation methods within the Domain Layer, per [34_Architecture_Principles.md](34_Architecture_Principles.md) — never bypassed by a direct field update from the Infrastructure Layer. Structural validation (required fields, format) is enforced at the Application Layer's DTO boundary, per the same document's Validation section. Both layers are required, per the same document's explicit statement that neither substitutes for the other.

## Cross-Store Integrity Summary

| Rule | Native Within PostgreSQL | Across Datastores |
|---|---|---|
| Foreign Keys | Native constraint | Logical FK: write-ordering + integrity sweep |
| Unique Constraints | Native, tenant-scoped composite | N/A (uniqueness is a single-store concept here) |
| Check Constraints | Native | N/A |
| Optimistic Locking | Version-column compare-and-swap | N/A (each store's own writes are independently optimistic-locked where applicable) |
| Transaction Boundaries | Native ACID transaction | Transactional outbox pattern |
| Immutable IDs | Application-generated UUID, never reused | Same ID used consistently as the join key across all stores |
| Immutable Audit History | DB-level trigger + no application code path | N/A (Audit Event is PostgreSQL-only) |
| No Orphan Records | `ON DELETE` behavior | Multi-step tracked deletion workflow |
| Relationship Validation | N/A (FKs suffice) | Application-layer validation before Neo4j write |
| Entity Validation | Domain Layer invariants + DTO validation | Same pattern, applied per entity regardless of target store |

## Responsibilities

- Every new cross-store relationship introduced in a later phase must be classified as either a same-store Foreign Key or a Logical Foreign Key, with the corresponding enforcement pattern from this document applied — an unenforced cross-store reference is a review-blocking finding.
- The transactional outbox pattern is mandatory for any write requiring propagation to a secondary store; ad hoc "write to Postgres, then immediately call the secondary store inline" code (without an outbox record) is prohibited, since it offers no retry guarantee if the inline call fails after the Postgres transaction commits.

## Constraints

- This document does not specify the exact outbox table schema, trigger syntax, or Cypher validation query — Deferred to Architecture-time implementation.
- "Defense in depth" language in rule 7 does not imply every rule requires two enforcement layers; it is specifically called out where the audit-immutability guarantee's importance warrants it.

## Future Considerations

- As outbox volume grows, its own retention and cleanup (outbox records for long-confirmed propagations) should follow the same Soft Delete → Retention Sweep pattern as any other entity, once outbox record volume becomes operationally significant.

## Acceptance Criteria

- [ ] All ten integrity rules from the governing specification are defined with a concrete enforcement mechanism.
- [ ] Every rule explicitly addresses both the single-store and cross-store case, given the polyglot persistence architecture — no rule is stated only in the abstract.
- [ ] The transactional outbox pattern is defined as the binding mechanism for cross-store write propagation, consistent with [41_Data_Architecture.md](41_Data_Architecture.md)'s consistency resolution.
