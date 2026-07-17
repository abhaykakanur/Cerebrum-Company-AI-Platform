# 34 — Architecture Principles

## Purpose

This document defines the universal architectural principles and patterns applied across every component and domain in Cerebrum, and specifies the internal architecture of the three sublayers — Application, Domain, Infrastructure — referenced throughout [31_Component_Architecture.md](31_Component_Architecture.md) and [35_Domain_Architecture.md](35_Domain_Architecture.md). Where those documents say "per the Application Layer pattern," this document is the definition being referenced.

## Scope

This document covers universal, cross-cutting architectural principles and the generic shape of the Application/Domain/Infrastructure sublayers. It does not restate per-component or per-domain specifics — see [31_Component_Architecture.md](31_Component_Architecture.md) and [35_Domain_Architecture.md](35_Domain_Architecture.md) for those.

## Definitions

- **Aggregate** — A cluster of domain entities and value objects treated as a single consistency boundary, accessed only through its root entity.
- **Value Object** — An immutable domain object defined entirely by its attributes, with no identity of its own (e.g., a `Citation` or `ConfidenceScore`).
- **Specification (pattern)** — An object encapsulating a business rule as a reusable, composable predicate, distinct from the "Specification" documents in this CES.
- Other terms per [10_Glossary.md](10_Glossary.md).

## SOLID and Foundational Principles

### Separation of Concerns
Every module has exactly one axis of change. This is enforced structurally: presentation (Frontend), business rules (domain/), orchestration (application/), and technical detail (infrastructure/) are always distinct packages, never interleaved in one file or class, per [33_Directory_Structure.md](33_Directory_Structure.md).

### Single Responsibility
Every class has exactly one reason to change. Applied concretely: a domain entity changes only when its business rules change; a repository adapter changes only when its storage technology's access pattern changes. A class serving two of these purposes (e.g., an entity that also formats HTTP responses) is a review-blocking violation.

### Dependency Inversion
High-level modules (domain, application) never depend on low-level modules (infrastructure); both depend on abstractions (ports) owned by the high-level module. This is the specific mechanism by which the Non-Negotiable Extraction Seam in [30_System_Architecture.md](30_System_Architecture.md) is achieved: a domain's repository port is defined in `domain/`, and every infrastructure adapter implementing it lives in `infrastructure/`, injected at composition time (see Dependency Injection below).

### Open/Closed Principle
Modules are open for extension, closed for modification. Applied concretely in the Connector Layer (FR-CN-012): adding connector #24 extends the system by adding a new `ConnectorPort` implementation, without modifying the Connector Layer's shared orchestration code, the Knowledge Ingestion Domain, or any other existing module.

### Composition over Inheritance
Domain and application logic is built by composing small, focused objects and functions rather than deep inheritance hierarchies. Shared behavior across domains (e.g., audit-logging on state change) is composed via explicit collaborator objects or domain events, not via a shared base class carrying behavior. `core/domain/` (see [33_Directory_Structure.md](33_Directory_Structure.md)) provides only structural base types (`Entity`, `ValueObject`), never behavior-carrying base classes.

### Explicit Dependencies
A class's or function's dependencies are always visible in its constructor or function signature — never resolved via global state, service-locator lookups, or hidden singletons. This directly supports testability (every dependency can be substituted with a test double) and Observability (every dependency is a visible edge in the dependency graph).

### Immutable Domain Models (where possible)
Value objects are always immutable. Entities are mutable only through explicit, named methods that enforce invariants on every transition (never through direct field assignment from outside the entity) — this is what "where possible" qualifies: entities have identity and lifecycle and therefore cannot be fully immutable, but every mutation is intentional and validated, never incidental.

### Dependency Injection
Every adapter implementing a domain-owned port is injected at application composition/startup (`core/di/`, see [33_Directory_Structure.md](33_Directory_Structure.md)), never instantiated directly inside domain or application code. This is the concrete mechanism realizing Dependency Inversion at runtime.

## Architectural Patterns

### Domain-Driven Design (DDD)
Cerebrum's 30 functional domains from [20_Functional_Requirements.md](20_Functional_Requirements.md) are realized as DDD bounded contexts. Each owns its own ubiquitous language (the requirement, entity, and value-object names used consistently from [10_Glossary.md](10_Glossary.md) through to code), its own aggregates, and communicates with other bounded contexts only through published application-service interfaces — never shared mutable state. See the Domain Layer Architecture section below for the tactical patterns applied within each bounded context.

### Clean Architecture / Hexagonal Architecture
These two patterns are applied together as one coherent rule, already stated structurally in [31_Component_Architecture.md](31_Component_Architecture.md): dependencies point inward (infrastructure → application → domain), and the domain is fully unaware of any delivery mechanism (HTTP, message queue) or storage technology. "Hexagonal" specifically names the domain/application core as the hexagon and every technology integration (database, LLM provider, search engine, HTTP API) as a port-and-adapter pair around it — there is no architecturally privileged adapter (e.g., the HTTP API is not more "central" than the Celery task adapter that also invokes the same application service).

### Layered Architecture
The domain/application/infrastructure triad is itself a layered architecture, with the additional Frontend Layer, and cross-cutting layers (Authorization, Monitoring, Configuration) forming the system-level layering in [30_System_Architecture.md](30_System_Architecture.md). Layered Architecture and Hexagonal Architecture are complementary here, not competing: layering describes the coarse system structure; hexagonal/clean describes the fine structure within each domain.

### CQRS-Ready
Cerebrum does NOT implement full CQRS (separate write and read models/datastores) in Version 1.0, but every domain's application layer already separates **command handlers** (state-mutating use cases, e.g., `CreateWorkspace`) from **query handlers** (read-only use cases, e.g., `GetWorkspace`), each with its own DTO shape. This separation is what makes CQRS-readiness real rather than aspirational: introducing a dedicated read model for a specific domain later (e.g., a denormalized read store for Enterprise Search) requires changing only that domain's query handlers and infrastructure, not its command side or any other domain.

### Event-Driven-Ready
Every domain's significant state changes are modeled as **domain events** (e.g., `WorkspaceCreated`, `ConnectorSyncCompleted`, `DecisionRecorded`) raised by aggregates at the point of change, even in V1.0 where these events are currently consumed synchronously, in-process, by explicit subscriber code (e.g., the Audit Domain subscribing to every domain's events to satisfy FR-AU-001) rather than published to an external message broker. This is what "ready," not "implemented," means: introducing an actual message broker (e.g., for the Analytics Layer's asynchronous event recording per [31_Component_Architecture.md](31_Component_Architecture.md)) is a matter of adding a broker-backed event-dispatcher infrastructure adapter, not redesigning how domains raise events.

### Plugin-Ready
Two components are explicitly designed around a plugin model: the Connector Layer (one plugin per source system, implementing `ConnectorPort`) and the AI Layer's provider adapters (one plugin per LLM/embedding provider, implementing `LLMProviderPort`/`EmbeddingProviderPort`). Both follow the same rule: a plugin is a self-contained infrastructure adapter, registered at composition time, requiring zero changes to the domain or application code it plugs into.

## Application Layer Architecture

The Application Layer orchestrates domain objects to fulfill a specific use case; it contains no business rules of its own (those belong to the Domain Layer) and no technology-specific code (that belongs to the Infrastructure Layer).

- **Use Cases** — The application layer's core unit: one class or function per distinct, requirement-traceable operation (e.g., `DeactivateUserUseCase`, corresponding directly to FR-UM-004). Every use case in this sense corresponds to exactly one or a small cohesive group of Requirement IDs from [20_Functional_Requirements.md](20_Functional_Requirements.md).
- **Application Services** — A named, cohesive grouping of related use cases exposed as the domain's public contract to other domains and to the API Domain (e.g., a `WorkspaceApplicationService` grouping create/configure/transfer/delete/archive use cases).
- **Command Handlers** — Application services handling state-mutating use cases; always return either a success acknowledgment or a well-typed error, never the mutated entity's full state unless the use case is explicitly also a query.
- **Query Handlers** — Application services handling read-only use cases; always safe to retry, never mutate state, and are the natural extension point for CQRS-readiness described above.
- **DTOs (Data Transfer Objects)** — Explicit, validated (via Pydantic, see [32_Technology_Stack.md](32_Technology_Stack.md)) data shapes crossing the Application Layer's boundary in both directions; domain entities are never serialized directly across this boundary, preventing infrastructure or presentation concerns from leaking into the domain model.
- **Validation** — Input validation occurs at the Application Layer boundary (DTO validation) for structural/format correctness, and within the Domain Layer for business-rule correctness (e.g., "an organization cannot have zero owners" is a domain invariant, not a DTO format check). Both are required; neither substitutes for the other.
- **Transactions** — A single use case invocation corresponds to a single transaction boundary at the Infrastructure Layer (e.g., one SQLAlchemy Unit of Work per command handler invocation), ensuring the aggregate-consistency guarantees described below are never partially applied.

## Domain Layer Architecture

The Domain Layer contains business rules and is technology-agnostic: no framework import, no database or network call, is permitted here.

- **Entities** — Objects with identity and a lifecycle (e.g., `User`, `Workspace`, `DecisionRecord`), whose mutation methods enforce invariants.
- **Aggregates** — A consistency boundary rooted at one entity (the Aggregate Root); all mutation within the aggregate goes through the root, and no external reference to a non-root member of an aggregate is permitted, per the Immutable Domain Models principle above. Cross-aggregate consistency (e.g., between a `Decision` aggregate and the `KnowledgeGraph` entities it references) is handled via eventual consistency and domain events, never a single cross-aggregate transaction.
- **Value Objects** — Immutable, identity-less objects (e.g., `ConfidenceScore`, `Citation`, `PermissionGrant`) defined by their attributes.
- **Repositories** — Domain-owned port interfaces (e.g., `WorkspaceRepository`) describing persistence operations in domain terms (`findById`, `save`), implemented by Infrastructure Layer adapters. A repository interface never leaks a storage-technology concept (e.g., no SQL, no Cypher) into its signature.
- **Domain Services** — Business logic that does not naturally belong to a single entity (e.g., "determine whether two graph entities are likely duplicates" per FR-KG-004 spans two entities and is a domain service, not a method on either entity).
- **Domain Events** — Immutable records of a significant state change (e.g., `DecisionRecorded`, `ConnectorHealthDegraded`), raised by aggregates and consumed per the Event-Driven-Ready pattern above.
- **Business Rules** — Invariants enforced by entities and domain services, directly traceable to a requirement's acceptance criteria (e.g., FR-WS-003's "a workspace always has at least one active owner" is a `Workspace` aggregate invariant).
- **Specifications** — Reusable, composable predicate objects encapsulating a business rule for reuse across use cases (e.g., a `IsBelowConfidenceThreshold` specification used by both FR-CF-003's low-confidence handling and FR-AL-003's grounding analytics).
- **Factories** — Encapsulate the construction of entities/aggregates that require more than a plain constructor to establish their initial invariants (e.g., a `WorkspaceFactory` that ensures a newly created workspace is created with exactly one owner, satisfying FR-WS-003 from the moment of creation).

## Infrastructure Layer Architecture

The Infrastructure Layer contains every technology-specific adapter implementing a Domain- or Application-Layer port. Per [32_Technology_Stack.md](32_Technology_Stack.md):

- **Database Adapters** — SQLAlchemy-based repository implementations for PostgreSQL-backed domains.
- **LLM Providers** — Adapters implementing `LLMProviderPort`, one per supported model provider, isolated so a provider change never touches AI Layer domain/application code.
- **Embedding Providers** — Adapters implementing `EmbeddingProviderPort`, analogous to LLM Providers.
- **Vector Database** — The Qdrant adapter implementing the Knowledge Layer's vector-search port.
- **Knowledge Graph** — The Neo4j/Cypher adapter implementing the Knowledge Graph Domain's repository and traversal ports.
- **Storage Providers** — The MinIO/S3-API adapter implementing the Knowledge Storage Domain's content-storage port.
- **Caching** — The Redis-backed cache adapter implementing the Configuration Layer's and Authentication Layer's low-latency read ports.
- **Messaging** — The Celery/Redis-backed task-queue adapter implementing the Background Processing Layer's `Enqueue`/`Schedule` port (see [36_Background_Processing.md](36_Background_Processing.md)).
- **Search Providers** — The OpenSearch adapter implementing the Enterprise Search Domain's keyword/hybrid search port.
- **Logging** — The Structlog-based adapter implementing the shared instrumentation port exposed by the Monitoring Layer.
- **Monitoring** — The Prometheus/OpenTelemetry adapters implementing the Monitoring Layer's metrics and tracing ports.

## Responsibilities

- Every code review must verify that a proposed change respects the dependency-direction rules stated here and in [33_Directory_Structure.md](33_Directory_Structure.md); this is treated as a correctness concern, not a style preference.
- Any proposal to introduce an exception to a principle in this document (e.g., a domain that must, for a compelling reason, depend on a specific infrastructure technology directly) requires an ADR per [09_Governance.md](09_Governance.md).

## Constraints

- This document does not mandate specific class names beyond the pattern names used (Entity, Aggregate, Repository, etc.) — exact naming is Deferred to Architecture-time implementation style guides.
- CQRS-Ready and Event-Driven-Ready explicitly do NOT mean CQRS and event-driven architecture are implemented in V1.0 — see each section's explicit scope statement.

## Future Considerations

- As specific domains grow in complexity (most likely Knowledge Graph and AI Reasoning), they are candidates for genuine CQRS (separate read/write datastores) ahead of other domains, given their already-distinct read (traversal/generation) and write (extraction/ingestion) access patterns.

## Acceptance Criteria

- [ ] Every principle and pattern named in the governing specification (SoC, SRP, DIP, OCP, Composition over Inheritance, Explicit Dependencies, Immutable Domain Models, DI, DDD, Clean Architecture, Hexagonal Architecture, Layered Architecture, CQRS-Ready, Event-Driven-Ready, Plugin-Ready) is defined with a concrete Cerebrum-specific application.
- [ ] The Application, Domain, and Infrastructure Layer architectures each address every element the governing specification named for them.
- [ ] No principle is stated abstractly without a Cerebrum-specific example tying it to a requirement or component.
