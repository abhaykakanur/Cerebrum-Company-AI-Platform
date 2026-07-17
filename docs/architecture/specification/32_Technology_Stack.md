# 32 — Technology Stack

## Purpose

This document names and justifies every technology selected for Cerebrum's Version 1.0 implementation. Each selection is evaluated against the architectural principles in [04_Project_Principles.md](04_Project_Principles.md) and [34_Architecture_Principles.md](34_Architecture_Principles.md), not chosen by default or popularity alone.

## Scope

This document covers technology selection and justification only. It does not cover how these technologies are arranged into components (see [30_System_Architecture.md](30_System_Architecture.md) and [31_Component_Architecture.md](31_Component_Architecture.md)) or repository layout (see [33_Directory_Structure.md](33_Directory_Structure.md)). Specific version pins beyond major version, and configuration detail, are Deferred to Architecture-time implementation.

## Definitions

See [10_Glossary.md](10_Glossary.md). No new terms are introduced here.

## Programming Languages

| Language | Use | Justification |
|---|---|---|
| **Python 3.12+** | Backend (all 30 domains, AI Layer, Knowledge Layer, Connector Layer) | Dominant ecosystem for AI/ML tooling (embedding, extraction, NLP libraries), strong async support (needed for I/O-bound connector and retrieval workloads), mature web framework options, and the language the Knowledge/AI Layers' surrounding tooling ecosystem is built in. Python 3.12+ specifically for improved performance and typing features (`TypedDict`, generics) that support Immutable Domain Models and explicit typing. |
| **TypeScript** | Frontend (Next.js/React) | Static typing at the presentation layer catches integration errors against the API contract at compile time rather than runtime, directly supporting Correctness over Cleverness. |
| **SQL** | Relational data definition and query (PostgreSQL) | The standard, portable language for relational data; used for Identity, Workspace, Organization, User Management, Authorization, Audit, Configuration, and other structured, transactional domains. |
| **Cypher** | Knowledge graph query (Neo4j) | The native query language for the selected graph database; required for Knowledge Graph Domain traversal, entity/relationship queries per FR-KG-006. |

## Backend Frameworks

| Technology | Use | Justification |
|---|---|---|
| **FastAPI** | HTTP API framework (API Domain) | Native async support (matches Python 3.12's async model for I/O-bound AI/retrieval calls), automatic OpenAPI schema generation (supports FR-AP-006 API versioning discoverability), and native Pydantic integration for request/response validation. Chosen over Flask/Django for async-first design better suited to LLM-call-heavy request paths, and over Django specifically because Cerebrum does not need a full-stack batteries-included framework (admin UI, ORM-coupled views) given the modular monolith's own domain/application/infrastructure layering. |
| **Pydantic** | Data validation and settings management | Enforces explicit, validated data contracts at every application-layer boundary (DTOs, configuration), directly supporting Explicit Dependencies and validation requirements across nearly every domain's acceptance criteria. |
| **SQLAlchemy** | ORM / relational data-access adapter | Mature, widely adopted Python ORM with an explicit Unit-of-Work and Repository-friendly pattern, enabling Persistence Layer adapters to implement domain-owned repository ports cleanly (Dependency Inversion) rather than leaking ORM models into domain code. |
| **Alembic** | Relational schema migration | The standard migration tool paired with SQLAlchemy; required for the Versionable, production-grade schema evolution mandated by [09_Governance.md](09_Governance.md)'s schema versioning requirement. |

## Frontend Frameworks

| Technology | Use | Justification |
|---|---|---|
| **Next.js** | Frontend application framework | Server-side rendering and streaming support directly benefit the Conversation Domain's token-by-token AI response delivery and initial page load performance for Enterprise Search. |
| **React** | UI component model | Next.js's underlying library; industry-standard component model with the largest available ecosystem for the data-dense views Cerebrum requires (search facets, graph visualization, document preview). |

## AI/Orchestration Libraries — Evaluated

### LangChain — Evaluated, Adopted in Limited Scope Only

**Decision:** LangChain SHALL NOT be used as the core orchestration engine for the AI Reasoning or Retrieval Layers. It MAY be used, at architecture-implementation time, as a source of individual, swappable components (e.g., a specific document loader or text splitter utility) wrapped behind Cerebrum's own `LLMProviderPort`, `EmbeddingProviderPort`, and retrieval interfaces — never as the framework that owns orchestration control flow.

**Justification:** LangChain's core value proposition — a high-level orchestration framework — directly conflicts with two binding principles from [04_Project_Principles.md](04_Project_Principles.md): Explicit over Implicit and Dependency Inversion (domains must own their ports; a third-party framework must not own the control flow that domains depend on). Adopting LangChain as the reasoning/retrieval backbone would mean Cerebrum's core AI Philosophy commitments — grounding enforcement (FR-AR-001), citation verification (FR-CT-003), hallucination reduction (FR-AR-006) — are implemented *inside* a framework Cerebrum does not control the internals of, making them harder to test, audit, and explain, which directly undermines the Reasoning Transparency requirement (FR-AR-008). Enterprise-grade, auditable AI pipelines benefit from explicit, Cerebrum-owned orchestration code where every step (retrieve → assemble → generate → validate → cite → score) is a visible, independently testable function, not a framework-internal chain. This mirrors widely reported production experience that LangChain's abstractions add debugging friction at scale without a corresponding reliability benefit for well-defined, custom pipelines.

### LlamaIndex — Evaluated, Not Adopted for Core Pipeline

**Decision:** LlamaIndex SHALL NOT be used as the core indexing/retrieval framework. Its data-connector and document-parsing utilities MAY be evaluated as swappable Infrastructure Layer adapter implementations at architecture-implementation time, subject to the same wrapping constraint as LangChain above.

**Justification:** The same Dependency Inversion and Explicit-over-Implicit reasoning applies. Additionally, LlamaIndex's opinionated indexing abstractions would compete with, rather than complement, Cerebrum's own Knowledge Graph Domain and hybrid-search design (FR-ES-003), which spans three distinct stores (Qdrant, Neo4j, OpenSearch) in a way LlamaIndex's index abstraction does not natively model.

### Cerebrum's Own Orchestration Layer

**Decision:** Cerebrum SHALL implement its own retrieval and reasoning orchestration code within the Retrieval Layer and AI Layer application sublayers (see [31_Component_Architecture.md](31_Component_Architecture.md)), using the `LLMProviderPort` and `EmbeddingProviderPort` interfaces to remain provider-agnostic.

**Justification:** This is a direct, deliberate application of Hexagonal Architecture: the ports are owned by Cerebrum, third-party libraries and provider SDKs are adapters behind them, and no third-party framework sits between a domain and its own business rules.

## Data Processing Libraries

| Technology | Use | Justification |
|---|---|---|
| **Pandas** | Tabular data manipulation (Analytics Domain reporting, table-extraction post-processing) | Standard, mature tool for the tabular transformations FR-AL-001 through FR-AL-006 and FR-KP-002 require. |
| **NumPy** | Numerical operations (embedding vector manipulation prior to storage) | Underlying numerical foundation for nearly every Python embedding/ML library; required as a transitive and direct dependency. |
| **NetworkX** | In-memory graph algorithms (e.g., traversal-result post-processing, graph analytics not natively expressed in Cypher) | Complements Neo4j for algorithmic graph operations (e.g., centrality scoring for FR-ED-001 expert ranking) better expressed in Python than Cypher. |

## Authentication Technologies

| Technology | Use | Justification |
|---|---|---|
| **JWT (JSON Web Tokens)** | Session/access token format | Stateless, widely supported token format enabling the Authentication Layer's session validation (FR-AUTH-007) without a database round-trip on every request. |
| **OAuth2** | Delegated authentication protocol | Required for OAuth Readiness (FR-AUTH-004) and as the underlying protocol for OIDC-based SSO. |
| **SAML (future readiness)** | Enterprise SSO protocol | Named explicitly for SSO Readiness (FR-AUTH-005); not implemented in V1.0 but the Authentication Layer's port design accommodates it as a future adapter without core redesign. |

## Databases

| Technology | Use | Justification |
|---|---|---|
| **PostgreSQL** | Primary relational store: Identity, Workspace, Organization, User Management, Authorization, Configuration, Audit, Decision records, Notification state | ACID transactional guarantees required for tenancy, permissions, and audit correctness; mature multi-tenancy patterns (schema-per-tenant or row-level security, Deferred to Architecture per Open Question 3 in [11_Open_Questions.md](11_Open_Questions.md)); the most operationally mature choice for the modular monolith's core transactional data. |
| **Neo4j** | Knowledge Graph Domain store | Purpose-built for entity/relationship traversal (FR-KG-006) at the depth and flexibility the Knowledge Graph Domain requires; native Cypher traversal outperforms modeling graphs in a relational store for this access pattern. |
| **Qdrant** | Vector store for embeddings (semantic search) | Purpose-built vector database with strong filtering (metadata + vector hybrid queries), open-source, self-hostable — consistent with avoiding unnecessary vendor lock-in for a core retrieval dependency. |
| **Redis** | Caching, session store, rate limiting, task queue broker (see Background Processing below) | Low-latency in-memory store needed for Configuration Layer caching (FR-CG-001/002 low-latency reads) and Authentication Layer session lookups; doubles as the Celery broker, reducing infrastructure surface area. |

## Search

| Technology | Use | Justification |
|---|---|---|
| **OpenSearch** (or Elasticsearch) | Keyword and hybrid search, faceting (Enterprise Search Domain) | Mature, purpose-built full-text search engine with native faceting (FR-ES-005) and filtering (FR-ES-004) support; OpenSearch preferred over Elasticsearch by default for its Apache 2.0 licensing, avoiding the licensing-model risk Elastic's license changes have historically introduced for self-hosted enterprise deployments — final selection between the two is Deferred to Architecture-time procurement/licensing review. |

## Background Processing — Evaluated

### Options Considered

| Option | Strengths | Weaknesses for Cerebrum |
|---|---|---|
| **Celery** | Mature, large ecosystem, well-documented FastAPI/Redis integration, strong retry/scheduling support (`celery beat`) | Weaker native support for durable, multi-step workflow state (e.g., resuming a partially completed ingestion pipeline) without additional custom bookkeeping. |
| **Dramatiq** | Simpler API than Celery, sane defaults, good Redis integration | Smaller ecosystem and community than Celery; fewer battle-tested patterns for the DLQ and scheduling requirements in FR-CN-007/FR-KI-011. |
| **Temporal** | Purpose-built durable execution model — ideal fit for the multi-stage Knowledge Ingestion → Processing → Graph Extraction pipeline (FR-KI-011 failure isolation, FR-CN-007 retry) with first-class workflow state and visibility | Requires operating a separate Temporal server cluster, directly working against the Modular Monolith's "lower operational complexity" rationale for V1.0. |

### Decision

**Celery SHALL be used for Version 1.0's Background Processing Layer**, backed by Redis as the broker. **Temporal is the identified target for a future migration** once (a) pipeline complexity or scale outgrows Celery's workflow-state capabilities, or (b) the Knowledge Layer is extracted into an independent service per [31_Component_Architecture.md](31_Component_Architecture.md)'s extraction-seam guidance — at which point operating a dedicated Temporal cluster no longer conflicts with the monolith's operational-simplicity goal, since the extraction has already introduced additional operational surface area.

**Justification:** This decision directly follows the same reasoning as the Modular Monolith decision itself: Celery's lower operational footprint matches V1.0's priority of proving the product across 30 domains before paying for Temporal's operational cost, while explicitly preserving a migration path — the Background Processing Layer's `Enqueue`/`Schedule` contract in [31_Component_Architecture.md](31_Component_Architecture.md) is deliberately abstract enough that swapping the underlying engine from Celery to Temporal is an infrastructure-adapter change, not a domain redesign.

## Object Storage

| Technology | Use | Justification |
|---|---|---|
| **MinIO** | Raw document/original-file storage (Knowledge Storage Domain) | S3-API-compatible, self-hostable object storage; using the S3 API (rather than a MinIO-specific API) means production deployment can transparently target a managed cloud object store (e.g., a cloud provider's S3-compatible service) without an adapter rewrite — Deferred to Architecture for the specific production target. |

## Logging

| Technology | Use | Justification |
|---|---|---|
| **Structlog** | Structured logging library | Produces machine-parseable, structured (JSON-capable) logs required for the Audit Domain's queryable records (FR-AU-001) and for correlating logs with traces in the Monitoring Layer; plain-text logging would not meet the "queryable by resource, actor, time range" acceptance criteria across multiple audit requirements. |

## Monitoring and Tracing

| Technology | Use | Justification |
|---|---|---|
| **Prometheus** | Metrics collection | Industry-standard, pull-based metrics system with strong Kubernetes-ecosystem integration, directly supporting the System Health Monitoring and Performance Analytics requirements (FR-MN-001, FR-AL-005). |
| **Grafana** | Metrics/log visualization | Pairs natively with Prometheus for the Uptime Dashboard requirement (FR-MN-004). |
| **OpenTelemetry** | Distributed tracing instrumentation | Vendor-neutral tracing standard, avoiding lock-in to a specific tracing backend and directly supporting Reasoning Transparency (FR-AR-008) by making the AI Layer's multi-step pipeline traceable end-to-end. |

## Testing

| Technology | Use | Justification |
|---|---|---|
| **Pytest** | Backend unit/integration testing | The standard Python testing framework, with strong fixture support suited to testing domain/application layers in isolation from infrastructure (per Dependency Inversion, ports can be faked/mocked cleanly). |
| **Playwright** | End-to-end testing | Cross-browser, reliable automation for validating full user journeys (e.g., the "verify" workflow for UI-facing changes) across the Frontend Layer and its API integration. |
| **Vitest** | Frontend unit testing | Fast, native ESM-compatible unit testing for the TypeScript/React frontend, replacing slower legacy alternatives with a toolchain that matches Next.js's build tooling. |

## Deployment

| Technology | Use | Justification |
|---|---|---|
| **Docker Compose** | Local development and single-node deployment | Directly supports the Modular Monolith's "easier local development" rationale — the entire stack (Postgres, Neo4j, Qdrant, OpenSearch, Redis, MinIO, backend, frontend) can be brought up with one command. |
| **Kubernetes-Ready** | Production deployment target | The application is built container-first and stateless at the application-process level (session state in Redis, not in-process memory) so it can be deployed to Kubernetes for horizontal scaling (see [39_Performance_Targets.md](39_Performance_Targets.md)) without an application redesign, even though V1.0 does not mandate a specific Kubernetes distribution. |

## Responsibilities

- Any technology substitution proposed after this phase requires an ADR per [09_Governance.md](09_Governance.md) documenting why the originally justified choice no longer fits.
- The LangChain/LlamaIndex/Celery-vs-Temporal decisions above are binding architectural decisions, not preferences; a later phase adopting LangChain as a core orchestration dependency without a superseding ADR would violate this specification.

## Constraints

- This document does not pin exact minor/patch versions — that is a dependency-management, not architecture, concern.
- No technology listed here is adopted merely because it appeared in the governing specification's suggested list; each carries a justification specific to a requirement or principle it satisfies.

## Future Considerations

- The OpenSearch-vs-Elasticsearch decision should be finalized during architecture implementation based on current licensing terms at that time, which may have changed since this document was written.
- The Celery-to-Temporal migration trigger conditions should be tracked as a concrete, monitored threshold (e.g., pipeline failure/retry volume) once V1.0 is operating, rather than left as a qualitative judgment call.

## Acceptance Criteria

- [ ] Every technology named in the governing specification is addressed with an explicit justification or a reasoned rejection/deferral.
- [ ] LangChain and LlamaIndex are explicitly evaluated with a stated scope of adoption, not a blanket yes/no.
- [ ] Celery, Dramatiq, and Temporal are comparatively evaluated with a stated decision and migration trigger.
- [ ] No justification relies on popularity alone without connecting to a specific requirement or principle.
