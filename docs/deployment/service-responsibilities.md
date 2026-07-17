# Service Responsibilities

Each service below states what it owns, what it explicitly does not own
(per `docs/architecture/specification/42_Database_Responsibilities.md`'s
"Must never own" pattern), and its current configuration state at this
infrastructure-only milestone.

## PostgreSQL

- **Owns:** Structured enterprise metadata once application schema exists
  (organizations, workspaces, users, permissions, documents, audit —
  see `docs/architecture/specification/42_Database_Responsibilities.md`).
- **Must never own:** Vector embeddings, graph structures, binary file
  content, ephemeral cache state.
- **Current state:** Empty. No schema, no tables, no migrations — created
  only when Phase 3 (Knowledge Storage) begins.
- **Image:** `postgres:16-alpine`.

## Neo4j

- **Owns:** The Knowledge Graph (entities, relationships) once implemented.
- **Must never own:** Document full text, vector embeddings.
- **Current state:** Empty. No nodes, relationships, constraints, or
  indexes. The APOC plugin is provisioned proactively but unused.
- **Image:** `neo4j:5-community`.

## Redis

- **Owns:** Cache, session state, rate-limit counters, the Celery task
  broker.
- **Must never own:** The sole copy of any durable business fact — a Redis
  flush must only ever cause a performance degradation, never data loss,
  per `docs/architecture/specification/42_Database_Responsibilities.md`'s
  binding consistency-model constraint.
- **Current state:** Empty, no keys.
- **Image:** `redis:7-alpine`.

## Qdrant

- **Owns:** Embedding vectors and their similarity-search index, once
  Knowledge Processing (Phase 5) begins generating them.
- **Must never own:** The chunk's source text (a brief payload excerpt for
  debugging convenience is permitted; the authoritative text lives in
  PostgreSQL), any relationship/graph structure.
- **Current state:** No collections created.
- **Image:** `qdrant/qdrant:latest`.

## MinIO

- **Owns:** Original document binaries (uploaded files, images, PDFs,
  recordings).
- **Must never own:** Structured metadata about a binary, extracted text.
- **Current state:** One empty bucket (`cerebrum-documents` by default,
  see `.env.example`), created by the `minio-init` one-shot job. No
  objects.
- **Image:** `minio/minio:latest` (service) + `minio/mc:latest`
  (init job only).

## OpenSearch

- **Owns:** The keyword/hybrid search index, once Enterprise Search
  (Phase 7) begins indexing content.
- **Must never own:** Anything not already owned by PostgreSQL/Qdrant in
  authoritative form — OpenSearch's index is itself Derived Data.
- **Current state:** No indexes, mappings, or templates. Running in
  single-node development mode with the security plugin disabled — **not**
  a valid configuration beyond local development; see
  `troubleshooting.md`.
- **Image:** `opensearchproject/opensearch:2`.

## Cross-Cutting Note: Nothing Here Is Authoritative Yet

Every "Owns" statement above describes what each service **will** own once
the corresponding domain is implemented (see
`docs/architecture/specification/110_Implementation_Roadmap.md` for
phasing). At this infrastructure-only milestone, every service is
provisioned and empty — no schema, no collections, no indexes, no
documents. This is intentional: the CIS Prompt 2 scope is infrastructure
only.
