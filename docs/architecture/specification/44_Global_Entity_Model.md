# 44 — Global Entity Model

## Purpose

This document defines the universal structures every Cerebrum entity shares: the Base Entity Envelope (global identifier strategy), the Entity Category taxonomy, the Versioning Model, and the Content Provenance Envelope (AI-generated vs. human-authored distinguishability). [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md) assumes and references these structures rather than restating them per entity.

## Scope

This document covers universal, cross-entity structures. It does not cover entity-specific attributes (see [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md)) or lifecycle state transitions (see [45_Data_Lifecycle.md](45_Data_Lifecycle.md), which uses the lifecycle state field defined here).

## Definitions

- **Base Entity Envelope** — The set of fields every entity in Cerebrum carries, regardless of category.
- **Content-Bearing Entity** — An entity category whose primary purpose is holding or representing informational content (as opposed to purely structural/relational entities like Team Membership).

## Global Identifier Strategy: The Base Entity Envelope

Every entity, in every datastore, SHALL contain the following fields, directly implementing Data Architecture Principles 2, 3, 7, 9, 10, and 11 from [41_Data_Architecture.md](41_Data_Architecture.md):

| Field | Purpose | Principle |
|---|---|---|
| **Internal UUID** | Globally unique, immutable identifier; the entity's only primary key. | Principle 2, 3 |
| **Creation Timestamp** | When the entity was first created. | Principle 8 (relationship timestamping extends to entity creation) |
| **Last Modified Timestamp** | When the entity was last changed. | Supports staleness/freshness signals (FR-EM-009/010). |
| **Created By** | The actor (User, Connector sync process, or system pipeline) that created the entity. | Principle 9 (provenance) |
| **Modified By** | The actor that most recently modified the entity. | Principle 9, 10 (auditability) |
| **Version** | A monotonically incrementing integer marking the entity's optimistic-locking generation, distinct from the Versioning Model below (which applies to *content* versioning, e.g., Document Versions) — this field exists on every entity to prevent lost updates (see [48_Data_Integrity.md](48_Data_Integrity.md)). | Principle 7 |
| **Tenant ID** | The owning Organization's identifier. | Multi-tenancy — see [46_Multi_Tenancy.md](46_Multi_Tenancy.md). |
| **Workspace ID** | The owning Workspace's identifier (nullable only for Organization-scoped entities like Organization itself). | Multi-tenancy. |
| **Lifecycle State** | The entity's current state in its lifecycle state machine (see [45_Data_Lifecycle.md](45_Data_Lifecycle.md)). | Principle 1 (single authoritative state). |
| **Soft Delete Flag** (`deleted`, `deleted_at`, `deleted_by`) | Whether the entity is soft-deleted, per [47_Data_Governance.md](47_Data_Governance.md)'s Soft Delete Strategy. | Principle 11, 12 |

This envelope applies uniformly across PostgreSQL rows, Neo4j nodes (as properties), Qdrant payload fields, and MinIO object metadata — no entity, regardless of which datastore authoritatively owns it, is exempt.

## Entity Category Taxonomy

Every entity SHALL belong to exactly one of the following 30 categories, per Data Architecture Principle 1's single-ownership requirement applied to classification itself. Full detail per category (attributes, storage, relationships) is in [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md); this table states only the category's one-line definition and its owning functional domain from [35_Domain_Architecture.md](35_Domain_Architecture.md).

| # | Category | Definition | Owning Domain |
|---|---|---|---|
| 1 | Organization | The root tenant container. | Identity / Organization |
| 2 | Workspace | A sub-tenant container within an Organization. | Identity / Workspace |
| 3 | User | An individual account holder. | User Management |
| 4 | Connector | A configured integration with an external source system. | Connector |
| 5 | Knowledge Source | A logical source scope within a Connector. | Connector |
| 6 | Document | A unit of ingested knowledge content. | Knowledge Storage |
| 7 | Document Version | A historical or current version of a Document. | Knowledge Storage |
| 8 | Chunk | A retrieval-sized segment of a Document Version. | Knowledge Processing |
| 9 | Embedding | A vector representation of a Chunk. | Knowledge Processing |
| 10 | Knowledge Entity | A node in the Knowledge Graph. | Knowledge Graph |
| 11 | Knowledge Relationship | An edge in the Knowledge Graph. | Knowledge Graph |
| 12 | Conversation | A multi-turn dialogue session. | Conversation |
| 13 | Message | A single turn within a Conversation. | Conversation |
| 14 | Meeting | A recorded or transcribed meeting. | Meeting Intelligence |
| 15 | Decision | A recorded organizational decision. | Decision Intelligence |
| 16 | Project | A tracked initiative or body of work. | Enterprise Memory |
| 17 | Technology | A named technology, tool, or platform. | Knowledge Graph |
| 18 | Team | An organizational sub-group of Users. | User Management |
| 19 | Policy | A specialized Document representing organizational policy. | Enterprise Memory |
| 20 | Procedure | A specialized Document representing an operational procedure. | Document Management |
| 21 | Customer | A tracked external customer entity. | Enterprise Memory |
| 22 | Incident | A tracked operational incident. | Enterprise Memory |
| 23 | Memory | A categorized durable-memory record referencing other entities. | Enterprise Memory |
| 24 | Search Session | A record of a search query and its context. | Enterprise Search |
| 25 | Citation | A source attribution attached to an AI-generated claim. | Citation |
| 26 | Audit Event | An immutable record of a security- or governance-relevant action. | Audit |
| 27 | Configuration | A tunable system or product setting. | Configuration |
| 28 | Feature Flag | A togglable capability gate. | Configuration |
| 29 | Background Job | A unit or run of asynchronous background work. | (Background Processing Layer, cross-cutting) |
| 30 | Notification | A system-generated notice to a user. | Notification |

## Versioning Model

Applied to every entity category marked "Versioned: Yes" in [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md), directly implementing Data Architecture Principle 7 and FR-KS-003:

| Field | Purpose |
|---|---|
| **Major Version** | Incremented for a substantive content change (Deferred to Architecture for the exact major/minor/patch trigger heuristic). |
| **Minor Version** | Incremented for a smaller, non-breaking content change. |
| **Patch Version** | Incremented for a metadata-only or corrective change not altering substantive content. |
| **Original Timestamp** | When the very first version of this entity was created. |
| **Latest Timestamp** | When the current version was created. |
| **Author** | The User or system process that produced this version. |
| **Change Summary** | A human- or system-generated description of what changed from the prior version. |
| **Version Parent** | A reference to the immediately preceding version, forming a version chain (never overwritten — see Principle 7). |
| **Version Status** | Current or Superseded — exactly one version per entity lineage is ever "Current" at a time. |

This model is distinct from the Base Entity Envelope's per-row optimistic-locking `Version` integer: the Versioning Model tracks *content history* (multiple, individually retrievable, semantically meaningful versions), while the envelope's `Version` field tracks *concurrency control* (preventing two simultaneous writers from silently overwriting each other's change to the same row).

## Content Provenance Envelope

Applied to every entity category marked "AI/Human Distinguishable: Yes" in [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md), directly implementing Data Architecture Principle 6 and the AI Philosophy's transparency commitment from [01_Product_Vision.md](01_Product_Vision.md):

| Field | Purpose |
|---|---|
| **Provenance Type** | One of: `HUMAN_AUTHORED`, `AI_GENERATED`, `AI_EXTRACTED`, `SYSTEM_DERIVED`. `AI_GENERATED` denotes original synthesis (e.g., a meeting summary); `AI_EXTRACTED` denotes structured extraction from existing content (e.g., an entity pulled from a document) — this distinction matters because extraction failure modes (missed entity) differ from generation failure modes (hallucinated content). |
| **Generated By** | If AI-attributed: the specific model/provider and version used (supporting FR-AR-008 reasoning transparency and future model-quality analysis). If human-authored: the authoring User reference (already covered by Created By in the Base Envelope, restated here for query convenience on content-bearing entities). |
| **Human-Reviewed Flag** | Whether a human has reviewed and confirmed AI-generated or AI-extracted content (relevant to FR-KG-003/004's merge review and FR-DI-003's decision-reasoning capture, where AI-extracted rationale may await human confirmation). |

## Responsibilities

- Every new entity category added in a later phase must be assigned to a taxonomy slot in this document (or trigger an ADR adding a 31st category) before implementation.
- Every content-bearing entity's schema must include the Content Provenance Envelope fields; omitting them for a content-bearing entity is a review-blocking finding against Principle 6.

## Constraints

- This document does not specify exact enum value names, field types, or nullability rules beyond what is stated — Deferred to Architecture-time schema design.
- The 30-category taxonomy is exhaustive for Phase 0; a genuinely new category (not a specialization of an existing one, as Policy/Procedure are specializations of Document) requires governance review per [09_Governance.md](09_Governance.md).

## Future Considerations

- As the AI Layer's provider ecosystem grows, the "Generated By" field's provider/model identifier should align with whatever provider-registry mechanism the AI Layer's `LLMProviderPort` adapters use, to avoid two parallel naming schemes.

## Acceptance Criteria

- [ ] All ten Base Entity Envelope fields from the governing specification's Global Identifier Strategy are defined.
- [ ] All 30 entity categories from the governing specification are catalogued with a definition and owning domain.
- [ ] The Versioning Model includes all nine fields named in the governing specification's Versioning section.
- [ ] The Content Provenance Envelope gives a concrete mechanism for Principle 6, not just a restatement of the principle.
