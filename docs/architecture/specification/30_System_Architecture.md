# 30 — System Architecture

## Document Status

CES Version 1.0, Phase 0, Part 3. This document extends CES Phase 0 Parts 1 and 2 (documents 00–27) and does not rewrite them. It defines **how** Cerebrum is architected to satisfy the requirements in [20_Functional_Requirements.md](20_Functional_Requirements.md) within the constraints of [04_Project_Principles.md](04_Project_Principles.md). Where this document and Parts 1–2 conflict, raise an ADR per [09_Governance.md](09_Governance.md) rather than resolving informally.

## Purpose

This document is the master Software Architecture Document (SAD) for Cerebrum. It defines the architectural style, the fifteen high-level components that make up the system, their responsibilities and boundaries, and how they interact. It is the entry point into the rest of the Part 3 document set.

## Scope

This document covers system-level and component-level architecture. It does not cover: exhaustive per-domain interface definitions (see [35_Domain_Architecture.md](35_Domain_Architecture.md)), technology selection rationale (see [32_Technology_Stack.md](32_Technology_Stack.md)), or repository layout (see [33_Directory_Structure.md](33_Directory_Structure.md)). No application code, schema, or API payload definition appears in this document or any Part 3 document.

## Definitions

- **Modular Monolith** — A single deployable application internally partitioned into strictly bounded, independently reasoned-about modules, as opposed to either an undifferentiated monolith or a distributed microservices system.
- **Bounded Context** — A DDD term for a boundary within which a domain model is internally consistent; in this document, each of the 30 functional domains from [20_Functional_Requirements.md](20_Functional_Requirements.md) is realized as one bounded context.
- **Port** — An interface, owned by the domain or application layer, that infrastructure code implements. Ports are how Dependency Inversion is realized architecturally (see [34_Architecture_Principles.md](34_Architecture_Principles.md)).
- **Adapter** — An infrastructure-layer implementation of a port (e.g., a PostgreSQL adapter implementing a `UserRepository` port).
- **Extraction Seam** — A deliberately maintained boundary within the modular monolith clean enough that the module behind it could become an independent service without redesigning its domain model.

## Architectural Style: Modular Monolith

### Decision

Cerebrum Version 1.0 SHALL be built as a modular monolith: a single deployable backend application, internally organized into the 30 bounded contexts defined in [20_Functional_Requirements.md](20_Functional_Requirements.md) and [21_Domain_Model.md](21_Domain_Model.md), each logically isolated behind explicit interfaces. Cerebrum SHALL NOT be built as a microservices architecture in Version 1.0.

### Rationale

| Consideration | Modular Monolith (chosen) | Microservices (rejected for V1.0) |
|---|---|---|
| Local development | A single process to run and debug | Requires orchestrating many services locally |
| Debugging | Single call stack, single log stream, straightforward tracing | Distributed tracing required just to follow one request |
| Operational complexity | One deployable, one datastore topology to operate | Many deployables, service discovery, inter-service auth, network reliability concerns |
| Iteration speed | Cross-domain changes are a single PR and a single deploy | Cross-service changes require coordinated multi-repo, multi-deploy releases |
| Domain separation | Enforced by module boundaries and code review, not network boundaries | Enforced by network boundaries, at higher infrastructure cost |
| Future extraction | Preserved, if bounded contexts remain strictly isolated from day one | N/A — already extracted |

This directly implements the Engineering Philosophy's "Simple architecture over unnecessary complexity" and "Correctness over cleverness" from [04_Project_Principles.md](04_Project_Principles.md): Cerebrum's early-stage priority is proving product value across 30 functional domains, not paying the distributed-systems tax before it is earned.

### Non-Negotiable Constraint: Preserve the Extraction Seam

The modular monolith choice is only safe if domain isolation is real, not aspirational. Every bounded context SHALL:
1. Expose all cross-domain interaction exclusively through its defined public interface (ports), never through direct access to another domain's internal state, database tables, or ORM models.
2. Depend on other domains' ports only, never on their infrastructure adapters.
3. Contain no import, call, or reference that reaches into another domain's `infrastructure/` or internal `domain/` submodules (see [33_Directory_Structure.md](33_Directory_Structure.md)).

A future decision to extract a bounded context into an independent service SHALL require only: (a) standing up the extracted service behind the same port interface, and (b) replacing the in-process adapter with a network adapter (e.g., gRPC or REST client) implementing that same port. No domain model redesign SHALL be required. This is the direct architectural fulfillment of the specification's requirement that "the architecture must allow future extraction into independent services without requiring domain redesign."

## High-Level Components

Cerebrum's backend is organized into fifteen high-level components. Each component may contain several of the 30 functional domains; the mapping is stated in each component's description. See [21_Domain_Model.md](21_Domain_Model.md) for the domains' own ownership and dependency detail, and [35_Domain_Architecture.md](35_Domain_Architecture.md) for per-domain architectural detail.

### 1. Frontend Layer

- **Responsibility:** Renders the Conversation, Enterprise Search, Document Management, Knowledge Graph visualization, and Administration user interfaces; consumes the Backend Layer exclusively through the Public and Administrative API surfaces (API Domain).
- **Boundaries:** Contains no business logic beyond presentation and client-side validation. Never accesses a datastore directly. Never contains AI reasoning, retrieval, or permission-enforcement logic — those are server-side only, consistent with Security by Default.
- **Dependencies:** Backend Layer (via API Domain only).
- **Interaction:** HTTPS requests to the Backend Layer's Public API; the Frontend Layer holds no direct dependency on any other backend component.

### 2. Backend Layer

- **Responsibility:** Hosts the modular monolith application: all 30 functional domains' application and domain logic, request routing, and orchestration. This is the umbrella component containing most of the domain-driven bounded contexts (Identity, Workspace, Organization, User Management, Authentication, Authorization, Document Management, Decision Intelligence, Expertise Discovery, Administration, Configuration, Notification, and the API Domain's implementation).
- **Boundaries:** Delegates AI-specific reasoning to the AI Layer, retrieval-specific assembly to the Retrieval Layer, and knowledge-specific structuring to the Knowledge Layer rather than reimplementing their concerns.
- **Dependencies:** AI Layer, Retrieval Layer, Knowledge Layer, Persistence Layer, Authentication Layer, Authorization Layer, Configuration Layer (all via defined ports).
- **Interaction:** In-process module calls within the monolith process; no network hop between Backend Layer domains and the layers below in V1.0.

### 3. AI Layer

- **Responsibility:** Owns the AI Reasoning, Citation, and Confidence Domains: grounded answer generation, evidence synthesis, cross-document reasoning, query decomposition, response validation, hallucination reduction, citation attachment/verification, and confidence scoring.
- **Boundaries:** Never queries a datastore directly for content — it consumes only the Assembled Context handed to it by the Retrieval Layer. Never bypasses the Authorization Layer's permission filtering, which is enforced upstream in Retrieval before content reaches this layer.
- **Dependencies:** Retrieval Layer (for assembled, permission-filtered context), Configuration Layer (for AI configuration per FR-CG-001), Enterprise Memory (via Knowledge Layer) for freshness/staleness signals feeding confidence.
- **Interaction:** In-process calls from the Backend Layer's Conversation Domain handler; outbound calls to configured LLM Provider adapters (Infrastructure Layer) for generation.

### 4. Retrieval Layer

- **Responsibility:** Owns the Retrieval Domain and the query-execution side of the Enterprise Search Domain: hybrid retrieval, context assembly, source ranking, deduplication, token budgeting, and context validation.
- **Boundaries:** Never generates natural-language answers — that is the AI Layer's exclusive responsibility. Always applies Authorization Layer permission filtering before returning any candidate content.
- **Dependencies:** Knowledge Layer (for indexed content and graph traversal), Authorization Layer (permission filtering), Persistence Layer (search index and vector store access via adapters).
- **Interaction:** In-process calls from the AI Layer and directly from the Backend Layer's Enterprise Search request handlers.

### 5. Knowledge Layer

- **Responsibility:** Owns the Connector, Knowledge Ingestion, Knowledge Processing, Knowledge Storage, Knowledge Graph, Enterprise Memory, Meeting Intelligence, and Decision Intelligence Domains — the full pipeline from external content to structured, storable, graph-connected knowledge.
- **Boundaries:** Never serves a user-facing query directly — query-time access goes through the Retrieval Layer and Enterprise Search, both of which depend on but do not belong to this layer. Ingestion and processing are write-path only.
- **Dependencies:** Connector-specific external systems (via Connector Layer), Persistence Layer, Background Processing Layer (for asynchronous pipeline execution), Authorization Layer (permission metadata capture at ingestion).
- **Interaction:** Background Processing Layer jobs drive most Knowledge Layer activity (ingestion, processing, graph extraction); synchronous in-process calls handle direct manual upload and Document Management interactions.

### 6. Persistence Layer

- **Responsibility:** Provides the adapters implementing every domain's repository and storage ports across PostgreSQL, Neo4j, Qdrant, OpenSearch/Elasticsearch, Redis, and MinIO (see [32_Technology_Stack.md](32_Technology_Stack.md)).
- **Boundaries:** Contains no business logic — only data-access adapters implementing domain-owned port interfaces. Never invoked directly by the Frontend Layer.
- **Dependencies:** None within the application (it is the lowest architectural layer); depends outward on the underlying datastore infrastructure.
- **Interaction:** Called exclusively via dependency-injected adapters satisfying domain- and application-layer port interfaces (Dependency Inversion).

### 7. Connector Layer

- **Responsibility:** Owns the Connector Domain: authentication, connection validation, full/incremental sync, health monitoring, scheduling, retry, conflict handling, logging, and metadata extraction for all 23 supported source-system categories plus the extensibility framework for future connectors.
- **Boundaries:** Never writes directly to the Knowledge Storage Domain's final indexed representation — connector output feeds the Knowledge Ingestion Domain's pipeline, which owns normalization and downstream processing.
- **Dependencies:** External source systems (outbound), Background Processing Layer (sync execution), Security Layer/Domain (credential storage), Knowledge Layer (ingestion handoff).
- **Interaction:** Scheduled and manually triggered jobs executed via the Background Processing Layer; each connector is a plugin implementing a shared Connector port (see [35_Domain_Architecture.md](35_Domain_Architecture.md)).

### 8. Background Processing Layer

- **Responsibility:** Executes all asynchronous, long-running, or scheduled work: connector synchronization, document processing pipeline stages, embedding generation, entity/relationship extraction, index updates, and scheduled maintenance (retention enforcement, staleness detection).
- **Boundaries:** Contains no domain business rules of its own — it orchestrates calls into Knowledge Layer and Connector Layer domain/application services. See [36_Background_Processing.md](36_Background_Processing.md) for full detail.
- **Dependencies:** Persistence Layer (job/task state), Knowledge Layer, Connector Layer, Monitoring Layer (job observability).
- **Interaction:** Task queue-driven; producers (API request handlers, schedulers) enqueue tasks, workers consume and execute them.

### 9. Authentication Layer

- **Responsibility:** Owns the Authentication Domain: credential verification, session management, token issuance/refresh, MFA/SSO/OAuth readiness, and device trust.
- **Boundaries:** Never makes an authorization (permission) decision — it establishes *who* the actor is; the Authorization Layer decides *what* they can do.
- **Dependencies:** User Management Domain (Backend Layer), Persistence Layer (session/credential storage), Security Layer (secrets, token signing keys).
- **Interaction:** Invoked at the start of every authenticated request via middleware; issues a verified actor identity consumed by the Authorization Layer and all downstream domains.

### 10. Authorization Layer

- **Responsibility:** Owns the Authorization Domain: RBAC, permission inheritance, resource-scoped permission enforcement, least-privilege defaults, and permission-change auditing.
- **Boundaries:** Never bypassed by any other component for resource access decisions — this is the single enforcement point referenced by every domain's "permission-aware" requirements in [20_Functional_Requirements.md](20_Functional_Requirements.md).
- **Dependencies:** Authentication Layer (verified actor identity), Persistence Layer (role/permission storage), Audit Domain (Backend Layer, for change logging).
- **Interaction:** Invoked synchronously, in-process, by every domain that returns or mutates a permission-scoped resource (Enterprise Search, Retrieval, Document Management, Knowledge Graph, etc.).

### 11. Analytics Layer

- **Responsibility:** Owns the Analytics Domain: search, usage, knowledge-coverage, connector, performance, and adoption reporting, aggregated from event and log data produced across every other layer.
- **Boundaries:** Read-only with respect to operational data — never mutates domain state. Reports on data; does not enforce policy.
- **Dependencies:** Persistence Layer (analytics data store), Monitoring Layer (shared metrics pipeline where applicable), every domain producing analytics-relevant events.
- **Interaction:** Consumes events/logs asynchronously (via the Background Processing Layer or a dedicated event stream — see Open Questions) rather than synchronously blocking the request path that generated the event.

### 12. Monitoring Layer

- **Responsibility:** Owns the Monitoring Domain: real-time subsystem health, degradation alerting, uptime dashboarding, and the shared observability primitives (metrics, tracing) other layers emit into. See [38_Observability.md](38_Observability.md).
- **Boundaries:** Observes; never controls. Alerting triggers a Notification Domain event, not an automatic remediation action, in V1.0.
- **Dependencies:** Every layer (as an emitter of health signals, metrics, and traces).
- **Interaction:** Pull-based health checks (liveness/readiness) and push-based metrics/trace emission from every component.

### 13. Configuration Layer

- **Responsibility:** Owns the Configuration Domain: AI configuration, search configuration, feature flags, and system settings, with organization/workspace-scoped inheritance per FR-OR-003.
- **Boundaries:** Provides read access to configuration for every other layer but is the sole writer of configuration state.
- **Dependencies:** Persistence Layer (configuration storage), Organization Domain (Backend Layer, for scope inheritance).
- **Interaction:** In-process, low-latency reads from every layer that has tunable behavior (notably AI Layer, Retrieval Layer, Enterprise Search).

### 14. Administration Layer

- **Responsibility:** Owns the Administration Domain: consolidated workspace, user, and connector administration surfaces, and administrative delegation.
- **Boundaries:** Does not duplicate domain logic — it is a composed, permission-gated presentation of capabilities already owned by Workspace, User Management, and Connector Domains.
- **Dependencies:** Workspace Domain, User Management Domain, Connector Layer, Authorization Layer.
- **Interaction:** In-process orchestration calls into the domains it composes; exposed to the Frontend Layer via the Administrative API (API Domain).

### 15. Infrastructure Layer

- **Responsibility:** Owns cross-cutting technical concerns not specific to any domain: the Security Domain's encryption and secrets management, the API Domain's versioning and webhook delivery, deployment topology, and the adapter implementations that satisfy Persistence Layer, LLM Provider, and Embedding Provider ports.
- **Boundaries:** Contains no product business logic. Every adapter in this layer implements a port defined by a domain or application layer above it — the Infrastructure Layer never defines a port that a domain must conform to (Dependency Inversion).
- **Dependencies:** External cloud/runtime infrastructure (databases, object storage, secret managers, LLM APIs).
- **Interaction:** Injected into domain and application code via dependency injection at application startup; never imported directly by domain-layer code (see [34_Architecture_Principles.md](34_Architecture_Principles.md)).

## AI Architecture Overview

This section describes the AI Layer and Retrieval Layer's internal responsibility split at a conceptual level only; no prompt content, model selection, or implementation detail is specified here — see Open Questions in [40_Open_Questions.md](40_Open_Questions.md) for deferred specifics.

| Concern | Owning Layer | Conceptual Responsibility |
|---|---|---|
| Retrieval | Retrieval Layer | Fetch and rank candidate knowledge for a query, per FR-RT-001 through FR-RT-007. |
| Context Assembly | Retrieval Layer | Structure retrieved candidates into a source-attributed context object within token budget, per FR-RT-002, FR-RT-005. |
| Reasoning | AI Layer | Generate an answer strictly from assembled context, per FR-AR-001 through FR-AR-008. |
| Prompt Construction | AI Layer | Translate assembled context and query into a provider-agnostic prompt representation; the specific prompt template is Deferred to Architecture-time implementation, not specified here. |
| Citation | AI Layer (Citation Domain) | Attach, verify, and link source citations to every claim, per FR-CT-001 through FR-CT-004. |
| Confidence Scoring | AI Layer (Confidence Domain) | Compute and expose a confidence indicator per FR-CF-001 through FR-CF-004. |
| Memory | Knowledge Layer (Enterprise Memory Domain), consumed by AI Layer | Supplies categorized durable context (decision, project, policy, etc.) as retrieval input. |
| Hallucination Reduction | AI Layer, enforced across Reasoning and Citation | A cross-cutting control applied via response validation (FR-AR-005) and citation verification (FR-CT-003), not a separate pipeline stage. |
| Evaluation Pipeline | AI Layer, reporting into Analytics Layer | Ongoing measurement of grounding percentage and hallucination rate, feeding FR-AL-003; the evaluation methodology itself is Deferred to Architecture. |

The AI Layer and Retrieval Layer are deliberately separate components (not a single "AI service") so that retrieval quality can be iterated and evaluated independently of reasoning quality, and so that a future LLM provider change touches only the AI Layer's provider adapters, never the Retrieval Layer.

## Security Overview

Full security architecture detail is Deferred to a dedicated security architecture review beyond Phase 0; this section states the architectural placement of security concerns established in [20_Functional_Requirements.md](20_Functional_Requirements.md)'s Security Domain (FR-SC-001 through FR-SC-006).

- **Authentication** is enforced once, centrally, in the Authentication Layer's request middleware — no domain re-implements credential checking.
- **Authorization** is enforced centrally in the Authorization Layer but invoked locally by every domain returning permission-scoped data — this is a deliberate exception to "enforce once centrally": permission checks must happen at the point of data return, not only at the request boundary, because a single request can touch many differently-scoped resources (e.g., a search result set spanning multiple documents).
- **Secrets Management** (FR-SC-003) is owned by the Infrastructure Layer via a dedicated secrets adapter, never by application-layer configuration files or environment variables holding raw secret values (see [37_Configuration_Strategy.md](37_Configuration_Strategy.md)).
- **Encryption at rest and in transit** (FR-SC-001, FR-SC-002) is enforced at the Persistence Layer and Infrastructure Layer boundary — every adapter connecting to a datastore or external service uses an encrypted transport, and every datastore is configured for encryption at rest at the infrastructure level, not the application level.
- **Tenant Data Isolation** (FR-SC-004) is enforced structurally: every persistence query issued by any domain is scoped by organization/workspace identifier as a mandatory, non-optional parameter at the repository-port level, not as an afterthought filter applied by callers.
- **Audit Logging** (Audit Domain) is emitted by every domain at the point of the audit-relevant action, not reconstructed after the fact from other logs.

## Component Interaction Summary

```
Frontend Layer
     |  (HTTPS, API Domain)
     v
Backend Layer  <----->  Authentication Layer
     |    |                    |
     |    +---> Authorization Layer <---+
     |                                   |
     +---> AI Layer ---> Retrieval Layer -+---> Knowledge Layer ---> Connector Layer ---> [External Systems]
     |         |               |                     |
     |         |               v                     v
     |         |         Persistence Layer <---- Background Processing Layer
     |         v
     |   Configuration Layer
     |
     +---> Administration Layer ---> (Workspace / User Mgmt / Connector, composed)

Cross-cutting, reachable from every layer above:
  Monitoring Layer, Analytics Layer, Infrastructure Layer (incl. Security)
```

This diagram is descriptive of dependency direction, not network topology — all arrows represent in-process calls in Version 1.0 except Connector Layer's arrow to External Systems.

## Responsibilities

- Every new capability proposed in a later phase must be placed into exactly one of the fifteen components above, or trigger an ADR proposing a sixteenth, per [09_Governance.md](09_Governance.md).
- Any code change that would violate the Non-Negotiable Extraction Seam constraint (direct cross-domain infrastructure access) must be rejected in review, not merged with a "fix later" annotation.

## Constraints

- This document does not specify deployment topology, container boundaries, or Kubernetes manifests — see [32_Technology_Stack.md](32_Technology_Stack.md) for deployment technology and Open Questions in [40_Open_Questions.md](40_Open_Questions.md) for what remains undecided.
- No component described here implies a specific class, module, or file name beyond what [33_Directory_Structure.md](33_Directory_Structure.md) establishes.

## Future Considerations

- Each of the fifteen components is a candidate for extraction into an independent service post-V1.0. The Knowledge Layer (ingestion/processing pipeline) and Connector Layer are the most likely first candidates given their asynchronous, resource-intensive nature relative to the request-synchronous Backend Layer.
- As usage scales, the Analytics Layer is a candidate for early extraction to an event-streaming architecture, since its read-heavy, eventually-consistent nature is architecturally distinct from the rest of the system's needs.

## Acceptance Criteria

- [ ] All fifteen high-level components from the governing specification are described with responsibility, boundaries, dependencies, and interaction.
- [ ] The Modular Monolith decision is justified against the rejected microservices alternative.
- [ ] The extraction-seam constraint is stated as a binding, verifiable rule, not an aspiration.
- [ ] AI architecture and Security architecture are addressed at the level this document's scope requires, with detail deferred to their dedicated documents/domains.
