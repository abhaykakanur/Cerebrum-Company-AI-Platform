# 45 — Data Lifecycle

## Purpose

This document defines the complete lifecycle of a Document and a Chunk from creation through deletion, mapping each stage to the owning datastore ([42_Database_Responsibilities.md](42_Database_Responsibilities.md)) and the Background Processing Layer workflow ([36_Background_Processing.md](36_Background_Processing.md)) that executes it. It also defines the general Lifecycle State model shared by every entity via the Base Entity Envelope ([44_Global_Entity_Model.md](44_Global_Entity_Model.md)).

## Scope

This document covers lifecycle *sequencing* and *state*. It does not redefine the processing logic within each stage (see the relevant domain in [35_Domain_Architecture.md](35_Domain_Architecture.md)) or retention/deletion governance rules (see [47_Data_Governance.md](47_Data_Governance.md), which this document's Retention and Deletion stages reference rather than duplicate).

## Definitions

- **Lifecycle Stage** — A discrete step in an entity's journey from creation to deletion, each with a defined entry condition, owning process, and exit condition.
- **Lifecycle State** — The Base Entity Envelope field recording which stage (or a higher-level grouping of stages) an entity currently occupies.

## Document Lifecycle

Every Document SHALL progress through the following stages, each mapped to its executing domain and datastore. This directly elaborates the Ingestion-to-Index Workflow from [36_Background_Processing.md](36_Background_Processing.md) with the data-architecture detail of what is written where at each step.

| # | Stage | Executing Domain | Primary Datastore Write | Notes |
|---|---|---|---|---|
| 1 | **Created** | Knowledge Ingestion | PostgreSQL (`Document` row, lifecycle state = `CREATED`) | The first write, per [41_Data_Architecture.md](41_Data_Architecture.md)'s consistency resolution — this row's existence is strongly consistent from this point forward. |
| 2 | **Uploaded** | Knowledge Ingestion | MinIO (original binary), PostgreSQL (object key reference, lifecycle state = `UPLOADED`) | Applies to manual/bulk upload and connector-sourced content alike (FR-KI-003). |
| 3 | **Validated** | Knowledge Ingestion | PostgreSQL (validation result) | Structural/format validation per [34_Architecture_Principles.md](34_Architecture_Principles.md)'s Application Layer Validation; a failure here routes to Ingestion Failure Recovery (FR-KI-011) rather than proceeding. |
| 4 | **Virus Scan** | Knowledge Ingestion (Infrastructure Layer adapter) | PostgreSQL (scan result flag) | A binary failing scan is quarantined (lifecycle state = `QUARANTINED`) and never proceeds to Text Extraction. |
| 5 | **Metadata Extraction** | Knowledge Ingestion | PostgreSQL (`Document` structural metadata, FR-KI-007) | |
| 6 | **Text Extraction** | Knowledge Processing | PostgreSQL (extracted text, pre-chunking) | FR-KP-001. |
| 7 | **Normalization** | Knowledge Processing | PostgreSQL (normalized text overwrites extraction-stage text — this is a pipeline-internal transformation, not a Document Version) | FR-KI-010, FR-KP-004. |
| 8 | **Language Detection** | Knowledge Ingestion | PostgreSQL (`Document.language`) | FR-KI-008. |
| 9 | **OCR (if required)** | Knowledge Processing | PostgreSQL (OCR text merged into extracted text, with confidence score, FR-KP-003) | Conditional stage — skipped for non-image-based content per FR-KI-009's routing logic. |
| 10 | **Chunk Generation** | Knowledge Processing | PostgreSQL (`Chunk` rows, one Document Version → many Chunks) | FR-KP-005; see Chunk Lifecycle below. |
| 11 | **Embedding Generation** | Knowledge Processing | Qdrant (`Embedding` vectors, one or more per Chunk) | FR-KP-009; this is the first Derived Data write to a secondary store, per [41_Data_Architecture.md](41_Data_Architecture.md), executed asynchronously and retried until confirmed. |
| 12 | **Entity Extraction** | Knowledge Processing | PostgreSQL (extraction result staging) | FR-KP-008, feeding stage 14. |
| 13 | **Relationship Extraction** | Knowledge Processing | PostgreSQL (extraction result staging) | FR-KP-008, feeding stage 14. |
| 14 | **Graph Linking** | Knowledge Graph | Neo4j (`Knowledge Entity`/`Knowledge Relationship` nodes/edges, FR-KG-001/002) | The second Derived Data write, independently retryable from Embedding Generation per [36_Background_Processing.md](36_Background_Processing.md)'s fan-out design. |
| 15 | **Indexing** | Enterprise Search | OpenSearch (search index entry) | FR-ES-001–003; independently retryable from Graph Linking, per the same fan-out design. |
| 16 | **Available for Retrieval** | Knowledge Storage | PostgreSQL (lifecycle state = `AVAILABLE`) | Set only once stages 11, 14, and 15 have all confirmed completion — this is the gate that FR-KI-012's ingestion reporting and FR-NT-005's completion notification key off. |
| 17 | **Version Updates** | Knowledge Storage | PostgreSQL (`Document Version` row, prior version's status → `Superseded`) | Re-entry point: a new version restarts stages 3–16 for the new content while the prior `Document Version` remains fully intact and retrievable, per FR-KS-003. |
| 18 | **Archived** | Knowledge Storage | PostgreSQL (lifecycle state = `ARCHIVED`) | FR-KS-005; excluded from default search (stage 15's index entry is marked inactive, not deleted). |
| 19 | **Retention** | Knowledge Storage | PostgreSQL (retention-eligibility evaluation against the applicable `RetentionPolicy`) | See [47_Data_Governance.md](47_Data_Governance.md) for policy definition; this stage only evaluates eligibility, it does not delete. |
| 20 | **Deletion** | Knowledge Storage | PostgreSQL (soft delete first; hard delete only via the retention-sweep Background Processing Task, per Principle 12 in [41_Data_Architecture.md](41_Data_Architecture.md)) | Cascades to Chunks, Embeddings, Knowledge Entities/Relationships derived solely from this Document, and the MinIO binary — see [48_Data_Integrity.md](48_Data_Integrity.md)'s No Orphan Records rule for cascade ordering. |

## Chunk Lifecycle

Every Chunk, created at Document Lifecycle stage 10, independently progresses through its own lifecycle:

| # | Stage | Executing Domain | Primary Datastore Write | Notes |
|---|---|---|---|---|
| 1 | **Chunk Created** | Knowledge Processing | PostgreSQL (`Chunk` row, linked to parent Document Version) | |
| 2 | **Chunk Metadata** | Knowledge Processing | PostgreSQL (`Chunk` structural metadata: sequence position, boundary type) | FR-KP-006. |
| 3 | **Embedding** | Knowledge Processing | Qdrant (`Embedding` vector) | FR-KP-009; corresponds to Document Lifecycle stage 11 for this specific Chunk. |
| 4 | **Semantic Index** | Enterprise Search / Retrieval | Qdrant (index availability confirmed) | The point at which this Chunk becomes eligible for FR-ES-002 semantic search and FR-RT-001 retrieval. |
| 5 | **Citation Mapping** | Citation | PostgreSQL (`Citation` rows created on-demand, referencing this Chunk, at AI-answer generation time — not a fixed pipeline stage but listed here for lifecycle completeness) | A Chunk does not need every downstream Citation created before being usable; this stage is best understood as "eligible to be cited," not "has been cited." |
| 6 | **Version Tracking** | Knowledge Storage | PostgreSQL (Chunk's implicit version via parent Document Version) | Per [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md), a Chunk's versioning is inherited, not independent. |
| 7 | **Knowledge Linking** | Knowledge Graph | Neo4j (entities/relationships sourced from this Chunk, if any) | Corresponds to Document Lifecycle stage 14, scoped to this Chunk's contribution. |
| 8 | **Search Availability** | Enterprise Search | OpenSearch (keyword index entry) | Corresponds to Document Lifecycle stage 15, scoped to this Chunk. |

A Chunk reaches full usability (semantic search, keyword search, and graph-linked) only when stages 4, 7, and 8 have all completed — mirroring the Document-level "Available for Retrieval" gate at a finer grain.

## General Lifecycle State Model

Every entity's Base Entity Envelope `Lifecycle State` field (per [44_Global_Entity_Model.md](44_Global_Entity_Model.md)) takes one value from a category-specific enumeration, but every enumeration SHALL include at minimum the following universal states, ensuring cross-category consistency for any tooling (e.g., Administration Layer views) that needs to reason about lifecycle state generically:

| Universal State | Meaning |
|---|---|
| `ACTIVE` (or a category-specific equivalent, e.g., `AVAILABLE` for Document) | The entity is fully usable for its intended purpose. |
| `PENDING` | The entity exists but has not completed the processing required to become `ACTIVE` (e.g., a Document mid-pipeline). |
| `ARCHIVED` | The entity is preserved but excluded from default active use, per FR-KS-005/FR-WS-006 pattern. |
| `SOFT_DELETED` | The entity is marked deleted and hidden from active use, per the Soft Delete Strategy in [47_Data_Governance.md](47_Data_Governance.md), but not yet purged. |
| `PURGED` | The entity has been hard-deleted via a retention-policy sweep; per Principle 12, this state is reached only through that path, never directly. |

Category-specific states (e.g., Document's `CREATED`/`UPLOADED`/`VALIDATED`/`QUARANTINED` pipeline states above, or User's `SUSPENDED`) extend this universal set; they do not replace it — every category-specific state maps onto exactly one of the five universal states for cross-category tooling purposes (e.g., `QUARANTINED` maps to `PENDING`, since the entity has not reached active usability).

## Responsibilities

- Every new content-processing capability introduced in a later phase must fit into the Document or Chunk lifecycle above, or extend it via a governance-reviewed addition, not bypass it.
- The Background Processing Layer's Task implementation for each stage (per [36_Background_Processing.md](36_Background_Processing.md)) must update the entity's Lifecycle State field as its final action, so the state always accurately reflects the last *completed* stage, never a stage in progress.

## Constraints

- This document does not specify exact retry/backoff parameters per stage — see [36_Background_Processing.md](36_Background_Processing.md) and Open Question 44 in [40_Open_Questions.md](40_Open_Questions.md).
- Stage numbering here matches the governing specification's presentation order; it does not imply every stage is strictly sequential — stages 11 (Embedding), 12–14 (Entity/Relationship/Graph), and 15 (Indexing) fan out and proceed independently per [36_Background_Processing.md](36_Background_Processing.md).

## Future Considerations

- As new content types are added (e.g., structured database connector content that does not require OCR or chunking in the same way), category-specific lifecycle variants should be defined while preserving the universal state model's cross-category consistency.

## Acceptance Criteria

- [ ] The full 20-stage Document Lifecycle from the governing specification is represented with an executing domain and datastore per stage.
- [ ] The full 8-stage Chunk Lifecycle from the governing specification is represented.
- [ ] A general Lifecycle State model is defined that every entity category can map onto, not just Document and Chunk.
