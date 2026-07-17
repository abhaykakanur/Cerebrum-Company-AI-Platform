# 107 — ADR Catalog

## Purpose

This document formalizes the twenty major architectural decisions made across this CES into standard Architecture Decision Records. Every decision recorded here was already made and justified in an earlier part; this catalog does not introduce new decisions — it is the canonical, governance-tracked record of decisions already taken, satisfying [09_Governance.md](09_Governance.md)'s requirement that every major architectural decision receive an ADR.

## Scope

This document covers the twenty ADRs named in the governing Part 10 specification. Each ADR cross-references the CES document where the decision was originally justified, rather than re-deriving the justification here.

## Definitions

- **Status** — An ADR's current standing: `Accepted` (in force), `Superseded` (replaced by a later ADR), `Deprecated` (no longer applicable, not replaced).

## ADR-001 — Modular Monolith

- **Status:** Accepted
- **Context:** Cerebrum comprises 30 functional domains requiring clear isolation, but the team and product are pre-scale; a distributed system pays operational cost before it is earned. See [30_System_Architecture.md](30_System_Architecture.md).
- **Decision:** Build Version 1.0 as a single deployable application with strictly enforced internal domain boundaries (Non-Negotiable Extraction Seam).
- **Consequences:** Faster iteration and simpler local development and debugging; requires disciplined enforcement (import-linting) to prevent boundary erosion.
- **Alternatives Considered:** Microservices from day one; undifferentiated monolith with no internal boundaries.
- **Trade-offs:** Slower to physically scale individual components independently until extraction occurs, in exchange for lower complexity now.
- **Future Review Date:** At Phase 6 (Knowledge Graph) kickoff, per [110_Implementation_Roadmap.md](110_Implementation_Roadmap.md) — the Knowledge Layer is the most likely first extraction candidate.

## ADR-002 — FastAPI

- **Status:** Accepted
- **Context:** The backend requires an async-first Python framework compatible with AI/retrieval call patterns. See [32_Technology_Stack.md](32_Technology_Stack.md).
- **Decision:** Use FastAPI for the API Domain and Backend Layer.
- **Consequences:** Native async support, automatic OpenAPI generation, Pydantic integration for DTO validation.
- **Alternatives Considered:** Flask (no native async), Django (batteries-included overhead not needed given the domain/application/infrastructure layering already provides structure).
- **Trade-offs:** Smaller batteries-included ecosystem than Django, offset by not needing Django's ORM-coupled patterns.
- **Future Review Date:** Not scheduled for review absent a specific performance or ecosystem-gap trigger.

## ADR-003 — Next.js

- **Status:** Accepted
- **Context:** The Frontend Layer requires server-side rendering/streaming for AI Chat token delivery and search performance. See [32_Technology_Stack.md](32_Technology_Stack.md).
- **Decision:** Use Next.js/React/TypeScript for the Frontend Layer.
- **Consequences:** SSR/streaming support for [89_AI_Chat_Architecture.md](89_AI_Chat_Architecture.md); largest available component ecosystem.
- **Alternatives Considered:** A plain React SPA without SSR; other meta-frameworks (Remix, SvelteKit).
- **Trade-offs:** Next.js-specific conventions add a learning curve, offset by ecosystem maturity and hiring pool size.
- **Future Review Date:** Not scheduled for review absent a specific trigger.

## ADR-004 — PostgreSQL

- **Status:** Accepted
- **Context:** Tenancy, permissions, and audit data require strong ACID transactional guarantees. See [41_Data_Architecture.md](41_Data_Architecture.md), [42_Database_Responsibilities.md](42_Database_Responsibilities.md).
- **Decision:** PostgreSQL is the authoritative relational datastore and the "first write" for every composite entity.
- **Consequences:** Strong consistency for tenancy/permissions/audit; the anchor for the eventual-consistency resolution across the polyglot stack.
- **Alternatives Considered:** MySQL, SQL Server — rejected for weaker native support for the Row-Level Security mechanism [46_Multi_Tenancy.md](46_Multi_Tenancy.md) depends on.
- **Trade-offs:** Not natively suited to graph or vector workloads, hence the polyglot approach (ADR-020) rather than forcing PostgreSQL to serve those needs.
- **Future Review Date:** At the multi-tenancy scale threshold named in Open Question 38/46_Multi_Tenancy.md's escape-hatch discussion.

## ADR-005 — Neo4j

- **Status:** Accepted
- **Context:** The Knowledge Graph Domain requires multi-hop relationship traversal at a depth and flexibility relational modeling does not efficiently support. See [42_Database_Responsibilities.md](42_Database_Responsibilities.md).
- **Decision:** Neo4j is the authoritative relationship datastore.
- **Consequences:** Native Cypher traversal for FR-KG-006; eventual consistency relative to PostgreSQL, per [41_Data_Architecture.md](41_Data_Architecture.md).
- **Alternatives Considered:** Modeling relationships in PostgreSQL via join tables — rejected as unable to efficiently support arbitrary-depth traversal at the target scale.
- **Trade-offs:** No native Row-Level Security, requiring query-layer tenant-isolation enforcement per [46_Multi_Tenancy.md](46_Multi_Tenancy.md).
- **Future Review Date:** At the per-tenant dedicated-database threshold named in [46_Multi_Tenancy.md](46_Multi_Tenancy.md).

## ADR-006 — Qdrant

- **Status:** Accepted
- **Context:** Semantic search and retrieval require a purpose-built vector datastore with hybrid vector+metadata filtering. See [42_Database_Responsibilities.md](42_Database_Responsibilities.md).
- **Decision:** Qdrant is the authoritative vector datastore.
- **Consequences:** Purpose-built ANN search with payload filtering supporting [46_Multi_Tenancy.md](46_Multi_Tenancy.md)'s pre-filter tenant isolation.
- **Alternatives Considered:** pgvector (PostgreSQL extension) — rejected for weaker performance at the target embedding volume; Pinecone/managed alternatives — rejected to avoid vendor lock-in, consistent with self-hostability preference.
- **Trade-offs:** An additional datastore to operate, offset by dedicated performance for its specific workload.
- **Future Review Date:** At the per-tenant dedicated-collection threshold named in [46_Multi_Tenancy.md](46_Multi_Tenancy.md).

## ADR-007 — Redis

- **Status:** Accepted
- **Context:** Session storage, caching, rate limiting, and the Celery broker all require low-latency, ephemeral storage. See [42_Database_Responsibilities.md](42_Database_Responsibilities.md).
- **Decision:** Redis is the authoritative cache and ephemeral store, and the Celery broker (ADR shared with background processing tooling, [32_Technology_Stack.md](32_Technology_Stack.md)).
- **Consequences:** Single technology serving multiple cross-cutting needs, reducing infrastructure surface area.
- **Alternatives Considered:** Memcached (no persistence options, less versatile), a dedicated message broker (RabbitMQ) separate from cache — rejected to avoid operating two systems where one suffices for V1.0 scale.
- **Trade-offs:** A Redis outage affects multiple concerns simultaneously (cache, sessions, queue) — mitigated by Redis never being the sole copy of durable data, per [42_Database_Responsibilities.md](42_Database_Responsibilities.md)'s binding consistency-model constraint.
- **Future Review Date:** Not scheduled absent a specific reliability trigger.

## ADR-008 — MinIO

- **Status:** Accepted
- **Context:** Original document binaries require S3-API-compatible object storage, self-hostable for development and portable to managed cloud storage in production. See [42_Database_Responsibilities.md](42_Database_Responsibilities.md).
- **Decision:** MinIO is the authoritative binary object store, accessed via the S3 API for production-target portability.
- **Consequences:** Development/production parity via a consistent API regardless of the underlying production target.
- **Alternatives Considered:** A cloud-native object store directly (e.g., a specific provider's S3 equivalent) — rejected as the sole option to preserve deployment flexibility across [96_Deployment_Strategy.md](96_Deployment_Strategy.md)'s multiple models.
- **Trade-offs:** Production object-storage target remains an open decision (Open Question 53).
- **Future Review Date:** At production infrastructure provisioning.

## ADR-009 — OpenSearch

- **Status:** Accepted
- **Context:** Keyword and hybrid search require a mature, purpose-built full-text search engine with faceting. See [32_Technology_Stack.md](32_Technology_Stack.md).
- **Decision:** OpenSearch is the default keyword/hybrid search engine, preferred over Elasticsearch primarily for Apache 2.0 licensing certainty.
- **Consequences:** Avoids the licensing-model risk Elastic's license changes have historically introduced.
- **Alternatives Considered:** Elasticsearch — remains a viable alternative pending final licensing review at implementation time.
- **Trade-offs:** OpenSearch's ecosystem is younger than Elasticsearch's, a minor maturity gap accepted for licensing certainty.
- **Future Review Date:** At implementation-time licensing review, per [32_Technology_Stack.md](32_Technology_Stack.md)'s own deferral.

## ADR-010 — Hybrid Retrieval

- **Status:** Accepted
- **Context:** Neither keyword nor semantic search alone consistently delivers enterprise-grade retrieval relevance. See [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md).
- **Decision:** Combine BM25, vector search, graph traversal, and eight other signals into a single configurable-weight ranked candidate set, per FR-RT-001/FR-ES-003.
- **Consequences:** Higher relevance than either method alone; requires tuning discipline (Open Question 89) and additional computational cost per query.
- **Alternatives Considered:** Semantic-only retrieval; keyword-only retrieval — both rejected as individually insufficient for the breadth of Query Classifications in [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md).
- **Trade-offs:** Retrieval latency vs. relevance quality, managed via the Knowledge Retrieval performance target ([39_Performance_Targets.md](39_Performance_Targets.md)).
- **Future Review Date:** After sufficient Evaluation Layer data accumulates to empirically tune default weights.

## ADR-011 — Grounded RAG (Retrieval-Augmented Generation)

- **Status:** Accepted
- **Context:** The AI Philosophy requires the AI to never be the source of truth. See [01_Product_Vision.md](01_Product_Vision.md), [50_AI_Architecture.md](50_AI_Architecture.md).
- **Decision:** Every factual AI response is grounded in retrieved Evidence via Cerebrum's own orchestration (not LangChain/LlamaIndex as the orchestration backbone, per [32_Technology_Stack.md](32_Technology_Stack.md)'s ADR-equivalent decision), with explicit validation and citation.
- **Consequences:** Directly enables Explainability, Citation, and Hallucination Reduction; requires the full Retrieval → Context Assembly → Reasoning → Validation pipeline ([51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md)) rather than a simpler direct-prompt approach.
- **Alternatives Considered:** Fine-tuning a model on organizational data instead of RAG — rejected as unable to provide per-response citation or handle continuously changing organizational knowledge without constant retraining.
- **Trade-offs:** Added latency and architectural complexity versus a bare LLM call, accepted as the necessary cost of grounding.
- **Future Review Date:** Ongoing, via [61_AI_Evaluation.md](61_AI_Evaluation.md)'s continuous Grounding Accuracy tracking.

## ADR-012 — Knowledge Graph

- **Status:** Accepted
- **Context:** Relationship-oriented questions ("who worked on X," "what depends on Y") are poorly served by document-only retrieval. See [35_Domain_Architecture.md](35_Domain_Architecture.md)'s Knowledge Graph Domain.
- **Decision:** Maintain an explicit entity/relationship graph (FR-KG-001–008), extracted from ingested content, as a first-class retrieval and reasoning input.
- **Consequences:** Enables Relationship, Dependency, and Timeline Reasoning ([56_Reasoning_Architecture.md](56_Reasoning_Architecture.md)); requires an extraction pipeline with inherent precision/recall limitations.
- **Alternatives Considered:** Inferring relationships purely at query time from document co-occurrence — rejected as too imprecise for dependency-finding use cases.
- **Trade-offs:** Extraction pipeline cost and eventual-consistency lag versus the value of explicit, traversable relationships.
- **Future Review Date:** At observed graph accuracy review, informed by [61_AI_Evaluation.md](61_AI_Evaluation.md) data.

## ADR-013 — Enterprise Memory

- **Status:** Accepted
- **Context:** Raw document retrieval alone does not capture categorized organizational context (decisions, projects, policies) needed for coherent, continuity-aware reasoning. See [59_Memory_Architecture.md](59_Memory_Architecture.md).
- **Decision:** Maintain nine categorized memory types (FR-EM-001–010) that augment, never replace, retrieval from authoritative sources.
- **Consequences:** Improves reasoning coherence and onboarding/continuity use cases; requires strict freshness governance to avoid the stale-memory failure mode identified in [59_Memory_Architecture.md](59_Memory_Architecture.md).
- **Alternatives Considered:** No dedicated memory layer, relying solely on per-request retrieval — rejected as insufficient for multi-turn coherence and category-specific context (e.g., Project Memory aggregation).
- **Trade-offs:** Additional data model complexity (a 31st-ish conceptual layer over existing entities) versus reasoning quality gains.
- **Future Review Date:** Following resolution of Open Question 80 (per-category freshness TTLs).

## ADR-014 — RBAC (Role-Based Access Control)

- **Status:** Accepted
- **Context:** Authorization needs a manageable, auditable, explainable access-control model for Version 1.0. See [77_Authorization_Model.md](77_Authorization_Model.md)'s Decision Rationale.
- **Decision:** RBAC for V1.0, with ABAC architected as future-ready but not built.
- **Consequences:** Simpler, more explainable permission model; the Permission Model's Scope field is designed for future ABAC extension without redesign.
- **Alternatives Considered:** ABAC from V1.0 — rejected as premature complexity per [04_Project_Principles.md](04_Project_Principles.md).
- **Trade-offs:** Less expressive than ABAC for edge-case, attribute-driven access rules, accepted pending demonstrated need.
- **Future Review Date:** Upon a concrete, recurring attribute-based access requirement emerging, per [77_Authorization_Model.md](77_Authorization_Model.md)'s Open Question 97.

## ADR-015 — Docker Compose (Development)

- **Status:** Accepted
- **Context:** Local development needs to bring up a five-datastore polyglot stack without per-developer manual installation. See [95_DevOps_Architecture.md](95_DevOps_Architecture.md)'s Decision Rationale.
- **Decision:** Docker Compose for Local Development; Kubernetes-ready for Staging/Production.
- **Consequences:** Fast, consistent onboarding; identical container images across environments.
- **Alternatives Considered:** Requiring a local Kubernetes cluster (e.g., minikube) for all developers — rejected as excessive overhead for day-to-day iteration.
- **Trade-offs:** Docker Compose does not exercise Kubernetes-specific behavior locally, requiring Staging as the first Kubernetes-faithful validation point.
- **Future Review Date:** Not scheduled absent a specific trigger.

## ADR-016 — Clean Architecture

- **Status:** Accepted
- **Context:** 30 domains require a consistent internal structure separating business rules from technical detail. See [34_Architecture_Principles.md](34_Architecture_Principles.md).
- **Decision:** Every domain follows the domain/application/infrastructure layering with inward-pointing dependencies.
- **Consequences:** Testability (mockable ports), technology substitutability, and the Non-Negotiable Extraction Seam's realization.
- **Alternatives Considered:** A simpler layered architecture without strict dependency inversion — rejected as insufficient to guarantee the extraction-seam property ADR-001 depends on.
- **Trade-offs:** More upfront structure/boilerplate per domain than an unstructured approach, justified at 30-domain scale.
- **Future Review Date:** Not scheduled; foundational and expected to remain stable.

## ADR-017 — Hexagonal Architecture

- **Status:** Accepted
- **Context:** Every domain integrates with multiple external technologies (databases, LLM providers, connectors) that must remain swappable. See [34_Architecture_Principles.md](34_Architecture_Principles.md).
- **Decision:** Ports-and-adapters applied uniformly — no adapter (HTTP, Celery task, CLI) is architecturally privileged over another.
- **Consequences:** Directly enables the Plugin-Ready pattern for Connectors ([66_Connector_SDK.md](66_Connector_SDK.md)) and AI Providers ([60_AI_Model_Abstraction.md](60_AI_Model_Abstraction.md)).
- **Alternatives Considered:** A framework-centric design where the web framework is architecturally central — rejected as coupling business logic to a specific delivery mechanism.
- **Trade-offs:** Same as ADR-016 — accepted as complementary, not additional, structural cost.
- **Future Review Date:** Not scheduled; foundational.

## ADR-018 — Domain-Driven Design

- **Status:** Accepted
- **Context:** 30 functional domains require a shared vocabulary and explicit bounded-context boundaries to avoid ambiguity at scale. See [34_Architecture_Principles.md](34_Architecture_Principles.md).
- **Decision:** Each of the 30 domains from [20_Functional_Requirements.md](20_Functional_Requirements.md) is realized as a DDD bounded context with its own aggregates, entities, and ubiquitous language traceable to [10_Glossary.md](10_Glossary.md).
- **Consequences:** Consistent terminology from requirements through architecture to code; clear aggregate consistency boundaries.
- **Alternatives Considered:** An anemic, transaction-script-style design without DDD tactical patterns — rejected as insufficient to enforce the business invariants (e.g., FR-WS-003) this specification requires.
- **Trade-offs:** DDD's learning curve for engineers unfamiliar with it, offset by the clarity it provides at this domain count.
- **Future Review Date:** Not scheduled; foundational.

## ADR-019 — Design System First

- **Status:** Accepted
- **Context:** A premium, consistent enterprise UI across dozens of pages requires a single visual source of truth. See [85_Frontend_Architecture.md](85_Frontend_Architecture.md).
- **Decision:** Build the Design System and Component Library before any page; no page may introduce custom styles outside it.
- **Consequences:** Visual consistency guaranteed by construction; a token change propagates platform-wide.
- **Alternatives Considered:** Page-by-page ad hoc styling with later consolidation — rejected as the path most SaaS products regret, producing visual drift that is expensive to unwind.
- **Trade-offs:** Slower initial page delivery (Design System must exist first) in exchange for long-term consistency and velocity.
- **Future Review Date:** At Component Library audit, per [87_Component_Library.md](87_Component_Library.md)'s Future Considerations.

## ADR-020 — Polyglot Persistence

- **Status:** Accepted
- **Context:** No single database technology efficiently serves relational, graph, vector, cache, and binary storage needs simultaneously. See [41_Data_Architecture.md](41_Data_Architecture.md).
- **Decision:** Five purpose-specific datastores (PostgreSQL, Neo4j, Qdrant, Redis, MinIO), each with exactly one responsibility, coordinated via a single-authoritative-write-plus-eventual-consistency pattern.
- **Consequences:** Each workload runs on its best-fit technology; requires the transactional outbox pattern ([48_Data_Integrity.md](48_Data_Integrity.md)) since no distributed transaction spans the heterogeneous stores.
- **Alternatives Considered:** A single general-purpose database (e.g., PostgreSQL with extensions for vector/graph) — rejected as under-performing dedicated technologies at the target scale ([41_Data_Architecture.md](41_Data_Architecture.md)).
- **Trade-offs:** Operational complexity of five datastores versus one, offset by Docker Compose (ADR-015) for development and Kubernetes-readiness for production scaling.
- **Future Review Date:** Not scheduled; foundational, revisited only if a specific datastore's fit is disproven by production data.

## Responsibilities

- Every ADR's Status must be updated (to Superseded or Deprecated) if a later governance decision changes it — this catalog must never present a superseded decision as still Accepted.
- Any new major architectural decision made during implementation must receive a new ADR (ADR-021 onward) following this same format, per [09_Governance.md](09_Governance.md).

## Constraints

- This document does not introduce any new decision — every ADR here formalizes a decision already justified in an earlier CES document, cited accordingly.

## Future Considerations

- As ADR-021 and beyond accumulate during implementation, this catalog should be split by topic area if it grows unwieldy as a single document.

## Acceptance Criteria

- [ ] All twenty ADRs from the governing specification are present with all eight required fields (Title, Status, Context, Decision, Consequences, Alternatives Considered, Trade-offs, Future Review Date).
- [ ] Every ADR cross-references the CES document where its decision was originally justified.
- [ ] No ADR introduces a decision not already established elsewhere in this CES.
