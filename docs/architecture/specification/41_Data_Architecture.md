# 41 — Data Architecture

## Document Status

CES Version 1.0, Phase 0, Part 4. This document extends CES Phase 0 Parts 1–3 (documents 00–40) and does not rewrite them. It defines Cerebrum's complete data architecture: how data is owned, structured, stored, versioned, isolated, and governed across the polyglot persistence stack named in [32_Technology_Stack.md](32_Technology_Stack.md) and placed architecturally in [30_System_Architecture.md](30_System_Architecture.md)'s Persistence Layer. This document is authoritative for every future implementation phase — no schema, migration, or ORM model may depart from it without an ADR per [09_Governance.md](09_Governance.md).

## Purpose

This document is the entry point into the Part 4 document set. It states the thirteen binding data architecture principles, the polyglot persistence model, and the rationale connecting Cerebrum's storage design to the requirements in [20_Functional_Requirements.md](20_Functional_Requirements.md) that depend on it (versioning, auditability, permission correctness, grounding/citation).

## Scope

This document covers principles and the top-level polyglot model. It does not cover per-datastore responsibility detail (see [42_Database_Responsibilities.md](42_Database_Responsibilities.md)), the entity-to-storage mapping (see [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md)), or the universal identifier envelope (see [44_Global_Entity_Model.md](44_Global_Entity_Model.md)). No database schema, migration script, or ORM model appears in this document or any Part 4 document.

## Definitions

- **Authoritative Owner** — The single datastore holding the system-of-record representation of a given piece of data; every other representation of that data elsewhere is derived.
- **Derived Data** — Data computed or copied from an authoritative source (e.g., a Qdrant embedding derived from a PostgreSQL-owned Chunk's text) that must always be traceable back to that source.
- **Polyglot Persistence** — Using multiple, purpose-specific datastore technologies within one system, each responsible for the class of data it is architecturally best suited to.
- **Strong Consistency** — A read is guaranteed to reflect the most recent completed write, enforced via ACID transactions.
- **Eventual Consistency** — A read may reflect a slightly stale state for a bounded period after a write, with the system guaranteed to converge to consistency once propagation completes.

## Data Architecture Principles

Each principle below is binding across every future implementation phase. Each is stated with its concrete Cerebrum-specific enforcement mechanism, not merely restated abstractly.

1. **Every piece of data has exactly one authoritative owner.** Enforced by the Canonical Storage Model below and detailed per-entity in [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md) — no entity's authoritative representation is ambiguous between two datastores.
2. **Every entity has a globally unique immutable identifier.** Enforced by the Global Identifier Strategy in [44_Global_Entity_Model.md](44_Global_Entity_Model.md) — a UUID assigned once at creation, never reassigned or reused, consistent with the Immutable IDs integrity rule in [48_Data_Integrity.md](48_Data_Integrity.md).
3. **Business identifiers shall never be primary keys.** A human-meaningful value (an email address, a source-system's native document ID, an organization's chosen slug) is always stored as a unique-constrained attribute alongside the internal UUID primary key, never as the key itself — this allows business identifiers to change (e.g., an email address update) without cascading identity changes through every relationship.
4. **Data duplication shall be minimized.** Where duplication is unavoidable for performance (e.g., a denormalized read-facing field), the duplicate is explicitly marked as Derived Data with a traceable source, never presented as a second authoritative copy.
5. **Derived data shall always identify its source.** Every Derived Data record (an embedding, a search index entry, a graph node extracted from a document) carries a reference back to the authoritative record it was derived from, satisfying the Citation Domain's and Retrieval Domain's traceability requirements from Part 2/3.
6. **AI-generated data shall always be distinguishable from human-authored data.** Enforced via the Content Provenance Envelope in [44_Global_Entity_Model.md](44_Global_Entity_Model.md), applied to every content-bearing entity category.
7. **Every important object shall be versioned.** Enforced via the Versioning Model in [44_Global_Entity_Model.md](44_Global_Entity_Model.md), directly implementing FR-KS-003 (Version History Retention) from Part 2.
8. **Every relationship shall be timestamped.** Every Neo4j relationship and every PostgreSQL join/association record carries a creation timestamp at minimum, satisfying FR-KG-005 (Graph Versioning) and FR-KG-007 (Entity and Relationship Timeline).
9. **Every entity shall maintain provenance.** Distinct from principle 6 (AI vs. human) and principle 5 (derived-data sourcing) — this is the broader requirement that every entity records *how* it came to exist (manual entry, connector sync, extraction pipeline, migration), detailed in [47_Data_Governance.md](47_Data_Governance.md).
10. **Every modification shall be auditable.** Enforced via the Audit Event entity category and the action list in [47_Data_Governance.md](47_Data_Governance.md), directly implementing FR-AU-001 from Part 2.
11. **Soft delete shall be preferred over hard delete.** Enforced via the Soft Delete Strategy in [47_Data_Governance.md](47_Data_Governance.md).
12. **Hard delete shall only occur through retention policies.** No ad hoc hard-delete code path exists anywhere in the system; hard deletion is exclusively a Background Processing Layer retention-sweep operation (see [36_Background_Processing.md](36_Background_Processing.md), [45_Data_Lifecycle.md](45_Data_Lifecycle.md)).
13. **Every storage technology shall have one clear responsibility.** Enforced via the Canonical Storage Model below and detailed in [42_Database_Responsibilities.md](42_Database_Responsibilities.md).

## Canonical Storage Model

Cerebrum SHALL use polyglot persistence across five datastore technologies, each with exactly one clear responsibility. No datastore duplicates another's responsibility as its authoritative owner (though Derived Data copies across stores are expected and are the mechanism by which each store serves its specialized access pattern).

| Datastore | Responsibility | Consistency Model |
|---|---|---|
| **PostgreSQL** | Authoritative relational datastore — structured enterprise metadata, tenancy, permissions, audit, configuration. | Strong (ACID transactions). |
| **Neo4j** | Authoritative relationship datastore — the Knowledge Graph and every graph derived from it (dependency, technology, project, people, decision, expertise graphs). | Eventual, relative to PostgreSQL's authoritative records that graph entities derive from. |
| **Qdrant** | Authoritative vector datastore — embeddings for semantic search and retrieval. | Eventual, relative to the PostgreSQL-owned Chunk it embeds. |
| **Redis** | Authoritative cache and high-performance temporary storage — sessions, rate limits, distributed locks, query cache. | Ephemeral by design; never the authoritative source for any durable business fact. |
| **MinIO** | Authoritative binary object storage — original files, images, PDFs, videos, audio, recordings, attachments. | Strong, for the binary itself, once written; referenced (not duplicated) by PostgreSQL metadata. |

This table restates and slightly extends the "SHALL be used" assignments from the governing specification; [42_Database_Responsibilities.md](42_Database_Responsibilities.md) provides the complete "Owns" enumeration per store.

## Strong vs. Eventual Consistency: The Central Architectural Resolution

The specification requires both "strong consistency where required" and "eventual consistency where appropriate." Cerebrum resolves this tension with one binding rule, elaborated fully in [48_Data_Integrity.md](48_Data_Integrity.md)'s Transaction Boundaries section:

**PostgreSQL is always the first write and the durability gate for any composite entity spanning multiple datastores.** A Document, Chunk, Knowledge Entity, or any other multi-store entity is created as a PostgreSQL row *first*, inside a single ACID transaction, before any corresponding Neo4j, Qdrant, or MinIO write is attempted. The PostgreSQL row's existence is strongly consistent and immediately queryable. The corresponding Neo4j/Qdrant/MinIO representations are Derived Data, written asynchronously by the Background Processing Layer's pipeline ([36_Background_Processing.md](36_Background_Processing.md)) with retry until confirmed, and are eventually consistent — a brief window may exist where a Document row exists in PostgreSQL but its embedding has not yet landed in Qdrant. This window is bounded, observable (via the pipeline's Task-completion tracking), and explicitly surfaced to users through the Enterprise Memory Domain's Freshness Signals (FR-EM-010) rather than hidden.

This is why Cerebrum does not attempt distributed transactions across heterogeneous datastores (which no combination of PostgreSQL, Neo4j, and Qdrant supports natively or safely) — it instead achieves correctness through a single authoritative write plus idempotent, retryable, eventually-consistent propagation, which is both the honest and the standard enterprise pattern for polyglot persistence at this scale.

## Relationship to Part 3 Architecture

This document's Canonical Storage Model is the data-layer realization of the Persistence Layer component described in [30_System_Architecture.md](30_System_Architecture.md) and the domain-owned Repository ports described in [34_Architecture_Principles.md](34_Architecture_Principles.md). Every domain's Repository port from [35_Domain_Architecture.md](35_Domain_Architecture.md) is implemented by an Infrastructure Layer adapter targeting exactly the datastore this document assigns as that entity's authoritative owner.

## Responsibilities

- Every future schema, migration, or ORM model must trace its target datastore to this document's Canonical Storage Model and its entity to [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md).
- Any proposal to store a class of data in a datastore other than its assigned authoritative owner requires an ADR per [09_Governance.md](09_Governance.md) justifying the departure from principle 13.

## Constraints

- This document does not specify column types, index definitions, or migration syntax — Deferred to Architecture-time implementation, strictly downstream of this specification.
- The Strong vs. Eventual Consistency resolution above is binding; a future implementation proposing a distributed-transaction approach across heterogeneous stores requires an ADR explaining why the eventually-consistent pattern is insufficient for the specific case.

## Future Considerations

- As Cerebrum's scale grows, the propagation-latency window between PostgreSQL's authoritative write and Neo4j/Qdrant's derived-write completion should be tracked as a first-class Monitoring Layer metric (extending [38_Observability.md](38_Observability.md)), since it directly bounds how "fresh" derived-data-dependent features (search, retrieval) can be.

## Acceptance Criteria

- [ ] All thirteen data architecture principles from the governing specification are stated with a concrete Cerebrum-specific enforcement mechanism.
- [ ] The Canonical Storage Model assigns exactly one authoritative owner per datastore responsibility, with no overlap.
- [ ] The strong-vs-eventual consistency tension is resolved with a single, explicit, binding rule rather than left ambiguous per-entity.
