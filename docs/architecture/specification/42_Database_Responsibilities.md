# 42 — Database Responsibilities

## Purpose

This document details the responsibility of each of the five datastore technologies in Cerebrum's Canonical Storage Model ([41_Data_Architecture.md](41_Data_Architecture.md)): what each owns, what it must never own, which domains from [35_Domain_Architecture.md](35_Domain_Architecture.md) read and write it, and its consistency model.

## Scope

This document covers per-datastore responsibility boundaries. It does not cover entity-level storage mapping (see [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md)) or tenant isolation mechanics per store (see [46_Multi_Tenancy.md](46_Multi_Tenancy.md), which this document's isolation notes point to rather than duplicate).

## Definitions

See [10_Glossary.md](10_Glossary.md) and [41_Data_Architecture.md](41_Data_Architecture.md). No new terms are introduced here.

## PostgreSQL

**Purpose:** Store structured enterprise metadata as the authoritative relational datastore.

**Owns:**

| Category | Notes |
|---|---|
| Organizations, Workspaces | Identity Domain, Workspace Domain, Organization Domain records. |
| Users, Permissions | User Management Domain, Authorization Domain records (roles, grants, inheritance rules). |
| Connectors | Connector Domain configuration and sync-run history (credentials themselves are Security Domain secrets, referenced not stored — see [37_Configuration_Strategy.md](37_Configuration_Strategy.md)). |
| Documents, Metadata | Knowledge Storage Domain's structured metadata (binary content is MinIO — see below). |
| Configurations, Feature Flags | Configuration Domain records. |
| Audit Events | Audit Domain's append-only records. |
| Search Sessions | Enterprise Search Domain's session state (durable history; active session state may additionally be cached in Redis). |
| Conversation Metadata | Conversation Domain's `Conversation` and `ConversationTurn` records. |
| Memory Metadata | Enterprise Memory Domain's `MemoryRecord` entries. |
| Jobs | Background Processing Layer's durable job history (distinct from Redis's ephemeral in-flight queue state — see Redis below). |
| Indexes | Metadata *about* indexes (e.g., which OpenSearch/Qdrant index a workspace's content lives in), not the index content itself. |
| Feature Flags, Statistics | Configuration Domain and Analytics Domain aggregated/summarized records. |
| Retention Policies | Knowledge Storage Domain's `RetentionPolicy` records. |
| Version History Metadata | Version pointers and metadata per [44_Global_Entity_Model.md](44_Global_Entity_Model.md)'s Versioning Model (the versioned binary itself, where applicable, lives in MinIO). |

**Must never own:** Vector embeddings, graph traversal structures, binary file content, or any data whose primary access pattern is similarity search or multi-hop relationship traversal — those belong to Qdrant and Neo4j respectively, per principle 13 in [41_Data_Architecture.md](41_Data_Architecture.md).

**Primary readers/writers:** Every domain in [35_Domain_Architecture.md](35_Domain_Architecture.md) except those whose primary data is graph- or vector-shaped (Knowledge Graph Domain writes summary/pointer rows only; Knowledge Processing Domain writes Chunk metadata rows, not embeddings).

**Consistency model:** Strong — every write is an ACID transaction; this is the datastore [41_Data_Architecture.md](41_Data_Architecture.md) designates as the "first write" for any composite, multi-store entity.

## Neo4j

**Purpose:** Store semantic relationships as the authoritative relationship datastore.

**Owns:**

| Category | Notes |
|---|---|
| Entities | Knowledge Graph Domain's `GraphEntity` nodes (FR-KG-001). |
| Relationships | Knowledge Graph Domain's `GraphRelationship` edges (FR-KG-002). |
| Knowledge Graph | The composed structure of the above two. |
| Temporal Relationships | Relationships carrying a validity time range (e.g., "was the tech lead of, from date X to date Y"), supporting FR-KG-007's timeline requirement. |
| Dependency Graph | The subset of the Knowledge Graph traversed for FR-KG-006/UC-10's "find dependencies" use case — not a separate physical graph, a query pattern over the same graph. |
| Technology Graph, Project Graph, People Graph, Decision Graph, Expertise Graph | Each a labeled subset/view of the same underlying Knowledge Graph, distinguished by node/relationship type, not separate Neo4j databases in V1.0 (see [46_Multi_Tenancy.md](46_Multi_Tenancy.md) for when per-tenant database separation may apply). |

**Must never own:** The authoritative text/binary content of a document or chunk (a PostgreSQL/MinIO responsibility — Neo4j nodes reference source content by ID, never duplicate its full text), vector embeddings (Qdrant's responsibility).

**Primary readers/writers:** Knowledge Graph Domain (read/write), Retrieval Domain and Enterprise Search Domain (read, for graph-based search FR-ES-006), Expertise Discovery Domain (read), Decision Intelligence and Meeting Intelligence Domains (write, via extraction pipeline).

**Consistency model:** Eventual relative to PostgreSQL — a graph node's existence always follows its PostgreSQL-owned source record's creation, per [41_Data_Architecture.md](41_Data_Architecture.md)'s central consistency resolution.

## Qdrant

**Purpose:** Store embeddings as the authoritative vector datastore.

**Owns:**

| Category | Notes |
|---|---|
| Embedding vectors | The numeric vector representations themselves. |
| Chunk vectors | One or more vectors per Knowledge Processing Domain `ProcessedContentChunk` (FR-KP-009). |
| Semantic search indexes | The vector index structure enabling FR-ES-002's semantic search. |
| Embedding metadata | The payload attached to each vector (tenant/workspace ID for filtering, source chunk reference, embedding model/version) — see [46_Multi_Tenancy.md](46_Multi_Tenancy.md) for the mandatory tenant-filtering payload fields. |
| Embedding version history | Pointer to which embedding model/version produced a given vector, supporting the re-embedding cutover mechanics referenced in Open Question 23 of [27_Open_Questions.md](27_Open_Questions.md). |

**Must never own:** The chunk's source text (PostgreSQL's responsibility — Qdrant payload may carry a short excerpt for debugging/display convenience, but the authoritative text lives in PostgreSQL), any relationship/graph structure (Neo4j's responsibility).

**Primary readers/writers:** Knowledge Processing Domain (write), Retrieval Domain and Enterprise Search Domain (read, for FR-ES-002/FR-RT-001).

**Consistency model:** Eventual relative to PostgreSQL, per the same rule as Neo4j above.

## Redis

**Purpose:** High-performance temporary storage as the authoritative cache.

**Owns:**

| Category | Notes |
|---|---|
| Cache | Configuration Domain's cached settings (FR-CG-001/002 low-latency reads, per [37_Configuration_Strategy.md](37_Configuration_Strategy.md)), Authorization Layer permission-decision cache. |
| Sessions | Authentication Domain's active `Session` state (FR-AUTH-007), fronting the durable PostgreSQL session history. |
| Rate limits | Authentication Domain (login attempts), API Domain (request throttling). |
| Temporary jobs | Celery's in-flight task queue state (distinct from PostgreSQL's durable job history — Redis holds only what is currently queued/executing). |
| Distributed locks | Connector Domain's per-connector execution lock (FR-CN-005's "manual trigger during in-progress sync is queued, not concurrent"). |
| Query cache | Enterprise Search Domain's hot-query result cache. |
| Short-term memory cache | Conversation Domain's active, in-progress conversation working state before it is persisted to PostgreSQL. |

**Must never own:** Any data whose loss would be a data-loss incident rather than a performance degradation — Redis is explicitly never the sole copy of a durable business fact, per principle 13 and the Consistency Model below.

**Primary readers/writers:** Nearly every domain, as a cross-cutting performance layer rather than a domain-specific store.

**Consistency model:** Ephemeral by design. A Redis outage or flush SHALL degrade performance (cache misses fall through to PostgreSQL, sessions require re-authentication) but SHALL NEVER cause permanent data loss of a business fact — this is a binding architectural constraint on how Redis may be used, not merely a description.

## MinIO

**Purpose:** Store binary objects as the authoritative object storage.

**Owns:**

| Category | Notes |
|---|---|
| Uploaded files | Knowledge Ingestion Domain's raw upload intake (FR-KI-001/002). |
| Images, PDFs, Office documents | Original-format binaries for Knowledge Storage Domain (FR-KS-001). |
| Videos, Audio, Meeting recordings | Meeting Intelligence Domain's source recordings (FR-MI-001). |
| Attachments | Any binary attached to a Document, Decision, or other entity rather than being the primary content. |
| Original document binaries | The exact bytes as uploaded/synced, distinct from any extracted text (PostgreSQL/Knowledge Processing's responsibility) or generated preview. |

**Must never own:** Structured metadata *about* a binary (that is a PostgreSQL row referencing the MinIO object key), extracted text content (Knowledge Processing Domain's PostgreSQL-owned output).

**Primary readers/writers:** Knowledge Ingestion Domain (write), Knowledge Processing Domain (read, for extraction), Document Management Domain (read, for download/preview FR-DM-001/002), Meeting Intelligence Domain (read/write).

**Consistency model:** Strong for the binary object itself once a write completes (MinIO/S3-API write-then-read consistency); the PostgreSQL metadata row referencing it is written first per [41_Data_Architecture.md](41_Data_Architecture.md), with the MinIO write following as part of the same Knowledge Ingestion pipeline stage, retried until confirmed per [36_Background_Processing.md](36_Background_Processing.md).

## Cross-Datastore Responsibility Summary

| If the data is... | It is owned by... |
|---|---|
| A business fact needing transactional integrity (identity, permissions, config, audit) | PostgreSQL |
| A multi-hop relationship or connection between entities | Neo4j |
| A similarity-searchable numeric representation of content | Qdrant |
| Ephemeral, reconstructable-on-miss, performance-only state | Redis |
| A binary file | MinIO |

## Responsibilities

- Any proposed write path that would place data in a datastore other than its owner per this document requires an ADR per [09_Governance.md](09_Governance.md).
- Every domain's Infrastructure Layer adapter (per [34_Architecture_Principles.md](34_Architecture_Principles.md)) must target exactly the datastore this document assigns as authoritative owner for the data it persists.

## Constraints

- This document does not specify table/collection/index schemas — Deferred to Architecture-time implementation.
- "Owns" in this document means authoritative system-of-record status; a datastore may hold a Derived Data copy of another store's data (e.g., Redis caching a PostgreSQL row) without that constituting ownership.

## Future Considerations

- As specific entity categories grow disproportionately large (e.g., Audit Events at enterprise scale), a dedicated time-series or cold-storage tier may be warranted for older records, without changing PostgreSQL's status as the authoritative owner of *current* records — Deferred to Architecture.

## Acceptance Criteria

- [ ] All five datastores' "Owns" lists from the governing specification are fully represented.
- [ ] Each datastore states what it must never own, preventing responsibility drift.
- [ ] Each datastore's consistency model is explicit and consistent with [41_Data_Architecture.md](41_Data_Architecture.md)'s central resolution.
