# 31 — Component Architecture

## Purpose

This document describes the internal architecture of each of the fifteen high-level components defined in [30_System_Architecture.md](30_System_Architecture.md): how each component is internally layered, what contract it exposes to other components, how it communicates with them, and where its future extraction seam lies. Where [30_System_Architecture.md](30_System_Architecture.md) answers "what is this component responsible for," this document answers "how is it built inside."

## Scope

This document covers component-internal structure and inter-component contracts. Universal architectural patterns applied across all components (Clean Architecture, Hexagonal Architecture, DDD tactical patterns, CQRS-readiness) are defined once in [34_Architecture_Principles.md](34_Architecture_Principles.md) and referenced, not redefined, here. Per-domain interface detail is covered in [35_Domain_Architecture.md](35_Domain_Architecture.md).

## Definitions

See [10_Glossary.md](10_Glossary.md) and the Definitions in [30_System_Architecture.md](30_System_Architecture.md). No new terms are introduced here.

## Universal Internal Layering Pattern

Every component that owns one or more functional domains follows the same three-sublayer internal structure, per Clean/Hexagonal Architecture (detailed in [34_Architecture_Principles.md](34_Architecture_Principles.md)):

```
Component
 └── domain/        — entities, value objects, domain services, ports (interfaces). No framework imports.
 └── application/    — use cases, command/query handlers, DTOs, orchestration. Depends on domain/ only.
 └── infrastructure/ — port adapters (DB, external API, cache). Depends on domain/ + application/ ports.
```

Dependency direction is always inward: `infrastructure` depends on `application` and `domain`; `application` depends on `domain`; `domain` depends on nothing else in the component. This is restated per-component below only where a component's composition (multiple domains, or a non-standard communication pattern) warrants elaboration.

## Component-by-Component Architecture

### 1. Frontend Layer

- **Internal structure:** Not a backend component; organized as a Next.js application with route-level pages, shared components, and a thin API-client library. No domain/application/infrastructure split applies — this layer contains presentation logic only.
- **Contract exposed:** None to other backend components; consumes the API Domain's Public API contract.
- **Communication pattern:** Synchronous HTTPS request/response; streaming (Server-Sent Events or WebSocket, Deferred to Architecture) for AI Layer token-by-token response delivery.
- **Extraction seam:** Already independently deployable from the Backend Layer; no further extraction work required.

### 2. Backend Layer

- **Internal structure:** A composition root containing the domain/application/infrastructure triads for Identity, Workspace, Organization, User Management, Authentication, Authorization, Document Management, Decision Intelligence, Expertise Discovery, Administration, Configuration, Notification, and API. Each domain's triad is isolated per the Non-Negotiable Extraction Seam constraint in [30_System_Architecture.md](30_System_Architecture.md).
- **Contract exposed:** The API Domain's Public, Internal, Administrative, and Connector API surfaces (FR-AP-001 through FR-AP-004).
- **Communication pattern:** In-process synchronous calls between contained domains' application-layer use cases; each domain calls another only through its published application-service interface, never its repositories directly.
- **Extraction seam:** Each contained domain is independently extractable per the standard seam; User Management and Authorization are the most likely first candidates given their use by every other domain (shared-kernel-adjacent gravity).

### 3. AI Layer

- **Internal structure:** `domain/` defines the Reasoning, Citation, and Confidence entities/value objects and the `LLMProviderPort` and `EmbeddingProviderPort` interfaces. `application/` contains the answer-generation use case orchestrating decomposition, synthesis, validation, citation attachment, and confidence scoring as an ordered pipeline. `infrastructure/` contains provider-specific adapters (see [32_Technology_Stack.md](32_Technology_Stack.md)).
- **Contract exposed:** A single `GenerateAnswer(query, assembledContext) -> AnswerResult` application service to the Backend Layer's Conversation Domain handler; `AnswerResult` bundles the answer text, citations, confidence score, and reasoning trace reference.
- **Communication pattern:** Synchronous in-process call for the orchestration; asynchronous/streaming for token delivery back to the Frontend Layer via the Backend Layer.
- **Extraction seam:** A natural service boundary — `LLMProviderPort` and `EmbeddingProviderPort` are already provider-agnostic, so extraction primarily requires wrapping the existing application service behind a network contract, not rewriting it.
- **Plugin-readiness:** New LLM or embedding providers are added as new `infrastructure/` adapters implementing the existing ports — no `domain/` or `application/` change required, directly satisfying Extensibility.

### 4. Retrieval Layer

- **Internal structure:** `domain/` defines `RetrievalCandidate`, `AssembledContext` value objects. `application/` contains the retrieval-and-assembly use case: hybrid retrieval invocation, source ranking, deduplication, token budgeting, context validation, in that pipeline order.
- **Contract exposed:** `AssembleContext(query, actor) -> AssembledContext` to the AI Layer and to the Backend Layer's Enterprise Search handlers (which consume ranked results directly rather than an assembled-for-reasoning context).
- **Communication pattern:** Synchronous in-process call, always invoking the Authorization Layer's permission filter before returning results.
- **Extraction seam:** Tightly coupled to the Knowledge Layer's search/graph read paths; extraction would need to preserve low-latency access to those indexes, making this a later-wave extraction candidate rather than an early one.

### 5. Knowledge Layer

- **Internal structure:** The largest component by domain count (Connector-adjacent ingestion handoff, Knowledge Ingestion, Knowledge Processing, Knowledge Storage, Knowledge Graph, Enterprise Memory, Meeting Intelligence, Decision Intelligence). Each domain retains its own internal domain/application/infrastructure triad; a shared `pipeline/` application-layer module orchestrates the ingestion → processing → storage → graph-extraction sequence as a composed workflow (see [36_Background_Processing.md](36_Background_Processing.md)).
- **Contract exposed:** `Ingest(rawContent, sourceMetadata) -> IngestionResult` (write path, mostly invoked by Background Processing) and read-side query services (`GetDocument`, `TraverseGraph`, etc.) consumed by Retrieval Layer and Backend Layer.
- **Communication pattern:** Asynchronous, job-driven for the write/pipeline path; synchronous in-process for read queries.
- **Extraction seam:** The strongest early-extraction candidate given its asynchronous, compute-intensive profile differs sharply from the Backend Layer's request-synchronous profile; the pipeline's stage boundaries (ingestion/processing/graph) are themselves internal extraction seams for a later, more granular split.

### 6. Persistence Layer

- **Internal structure:** No domain/application sublayers — this component *is* the infrastructure sublayer for every other component's persistence needs. Organized by datastore technology (`postgres/`, `neo4j/`, `qdrant/`, `opensearch/`, `redis/`, `minio/`), each providing adapters implementing the repository/store ports defined by the domains that use them.
- **Contract exposed:** Repository and store port implementations, injected at application composition/startup — never called directly by name from domain code.
- **Communication pattern:** Synchronous calls from adapters to their respective datastore; connection pooling and transaction management are Deferred to Architecture-time implementation detail.
- **Extraction seam:** N/A as a component (it is inherently infrastructure); individual datastore adapters can be swapped independently of one another because each domain depends only on its own port, not on the Persistence Layer as a monolithic unit.

### 7. Connector Layer

- **Internal structure:** `domain/` defines the `ConnectorPort` interface (authenticate, validate, fullSync, incrementalSync, reportHealth) that every connector plugin implements, plus shared value objects (`SyncResult`, `ConnectorHealth`). `application/` contains sync orchestration, retry policy, and conflict-handling use cases shared across all connectors. `infrastructure/` (here, `connectors/` at the repository root — see [33_Directory_Structure.md](33_Directory_Structure.md)) contains one plugin package per source-system category, each a `ConnectorPort` implementation.
- **Contract exposed:** `ConnectorPort` to the shared sync orchestration; sync results are hand off to the Knowledge Layer's `Ingest` contract.
- **Communication pattern:** Background Processing Layer-scheduled and manually triggered jobs invoke a connector plugin's `ConnectorPort` methods; results are enqueued for ingestion.
- **Extraction seam:** Individually pluggable per connector by design (FR-CN-012); the shared orchestration layer is the extraction unit if the whole Connector Layer is extracted, with each connector plugin traveling with it unchanged.
- **Plugin-readiness:** This is the primary Plugin-Ready component in the architecture — adding connector #24 requires only a new `ConnectorPort` implementation, zero changes to Knowledge Ingestion, Processing, Storage, or Authorization domains, directly satisfying FR-CN-012's acceptance criteria.

### 8. Background Processing Layer

- **Internal structure:** `application/` contains task definitions (one per background operation: sync execution, pipeline stage execution, retention sweep, staleness scan) and a scheduler. `infrastructure/` contains the task-queue broker adapter (see [32_Technology_Stack.md](32_Technology_Stack.md) and [36_Background_Processing.md](36_Background_Processing.md)).
- **Contract exposed:** `Enqueue(taskType, payload) -> TaskHandle` and `Schedule(taskType, cronExpression)` to any component needing asynchronous execution.
- **Communication pattern:** Asynchronous, queue-mediated; producers and consumers are decoupled in time, satisfying Event-Driven-Ready per [34_Architecture_Principles.md](34_Architecture_Principles.md).
- **Extraction seam:** Already logically decoupled via the queue; extraction to independently scaled worker fleets requires no architectural change, only deployment topology change.

### 9. Authentication Layer

- **Internal structure:** `domain/` defines `Credential`, `Session`, `DeviceTrust` entities. `application/` contains login, token-refresh, MFA-verification, and session-revocation use cases. `infrastructure/` contains password-hashing, JWT signing, and (future) SSO/OAuth provider adapters.
- **Contract exposed:** `Authenticate(credentials) -> AuthenticatedActor`, `ValidateSession(token) -> AuthenticatedActor`, invoked as request middleware ahead of every other component.
- **Communication pattern:** Synchronous, in-process, on the critical path of every authenticated request.
- **Extraction seam:** A common early-extraction candidate industry-wide (dedicated identity service); Cerebrum's port-based design supports this without disruption, though V1.0 keeps it in-process for latency and simplicity.

### 10. Authorization Layer

- **Internal structure:** `domain/` defines `Role`, `PermissionGrant`, `PermissionInheritanceRule`. `application/` contains the permission-evaluation use case, invoked as `CheckPermission(actor, resource, action) -> Decision` and `FilterByPermission(actor, resourceSet) -> resourceSet`.
- **Contract exposed:** The two methods above, to every component that returns or mutates permission-scoped resources.
- **Communication pattern:** Synchronous, in-process, called potentially many times per request (e.g., once per search result) — performance characteristics of this call are a first-class concern, see [39_Performance_Targets.md](39_Performance_Targets.md).
- **Extraction seam:** High call-frequency makes this a poor early extraction candidate under a naive network-call model; if extracted, a local caching/decision-point pattern (e.g., sidecar) would be required to preserve latency, Deferred to Architecture.

### 11. Analytics Layer

- **Internal structure:** `application/` contains report-generation use cases per FR-AL-001 through FR-AL-006. `infrastructure/` contains the analytics event ingestion adapter and the reporting datastore adapter.
- **Contract exposed:** `RecordEvent(eventType, payload)` (write, called by every domain producing analytics-relevant activity) and `GetReport(reportType, scope, timeRange) -> Report` (read, called by Administration Layer and the Frontend Layer).
- **Communication pattern:** Asynchronous for event recording (via Background Processing Layer, to avoid adding latency to the originating request); synchronous for report retrieval.
- **Extraction seam:** A strong early-extraction candidate given its naturally asynchronous, eventually-consistent nature; could migrate to a dedicated event-streaming pipeline without touching any producing domain's synchronous logic, since producers already call an abstract `RecordEvent` port.

### 12. Monitoring Layer

- **Internal structure:** No domain layer — this is a cross-cutting infrastructure concern. Provides a shared metrics/tracing/logging instrumentation library consumed by every other component, plus the Monitoring Domain's health-aggregation and alerting application logic.
- **Contract exposed:** Instrumentation primitives (structured logger, metrics emitter, tracer) importable by any component; `GetHealthStatus(subsystem) -> HealthStatus` for the Monitoring Domain's own read surface.
- **Communication pattern:** Push-based instrumentation (every component emits); pull-based health checks (external load balancer/orchestrator polls). See [38_Observability.md](38_Observability.md).
- **Extraction seam:** N/A — this component is designed to remain a shared library plus a lightweight aggregation service, not something "extracted" in the domain sense.

### 13. Configuration Layer

- **Internal structure:** `domain/` defines `ConfigurationSetting`, `FeatureFlag` with organization/workspace scope. `application/` contains the inheritance-resolution use case (FR-OR-003's cascading behavior).
- **Contract exposed:** `GetConfig(key, scope) -> value` (read, called by any component with tunable behavior) and `SetConfig(key, scope, value)` (write, called only by the Administration Layer).
- **Communication pattern:** Synchronous, in-process, cached aggressively given its read-heavy, low-churn access pattern (see [39_Performance_Targets.md](39_Performance_Targets.md) for caching strategy).
- **Extraction seam:** Low priority for extraction — its low write volume and criticality to every other component's latency favor keeping it in-process indefinitely, even post-microservices-migration, as a shared library backed by a fast cache.

### 14. Administration Layer

- **Internal structure:** `application/` only — no independent `domain/` beyond thin composition value objects (e.g., `AdministrativeDelegationGrant`). It orchestrates calls into Workspace, User Management, and Connector Layer application services rather than owning primary domain state.
- **Contract exposed:** Composed administrative use cases (`AdministerWorkspace`, `AdministerUser`, `AdministerConnector`) to the Administrative API surface.
- **Communication pattern:** Synchronous, in-process orchestration.
- **Extraction seam:** Extracts cleanly only after its constituent domains (Workspace, User Management, Connector) are themselves independently addressable; it is a composition layer, not a data owner.

### 15. Infrastructure Layer

- **Internal structure:** Organized by concern: `security/` (secrets, encryption key access), `api_versioning/`, `webhooks/`, and the provider-specific adapters that also serve the AI Layer and Persistence Layer (some adapters are shared/re-exported rather than duplicated).
- **Contract exposed:** Security primitives (`GetSecret`, `Encrypt`, `Decrypt`) and webhook delivery (`RegisterWebhook`, `Deliver`) to any component needing them.
- **Communication pattern:** Synchronous for secrets/encryption (low latency required); asynchronous for webhook delivery (via Background Processing Layer, with retry).
- **Extraction seam:** Secrets management is a common candidate for delegation to a managed external service (e.g., a cloud secrets manager) from day one at the infrastructure-provisioning level, even while remaining in-process at the application-architecture level.

## Cross-Component Communication Summary

| Pattern | Used Between | Rationale |
|---|---|---|
| Synchronous in-process call | Backend Layer ↔ AI/Retrieval/Authorization/Configuration Layers | Request-path latency requirements (see [39_Performance_Targets.md](39_Performance_Targets.md)) rule out network hops in V1.0. |
| Asynchronous queue-mediated | Knowledge Layer, Connector Layer, Analytics Layer ↔ Background Processing Layer | Long-running or bulk operations must not block request-serving capacity. |
| Streaming | AI Layer → Frontend Layer (via Backend Layer) | Token-by-token answer delivery for perceived responsiveness, per the Chat Response First Token target. |
| Pull-based health check | Monitoring Layer ← every component | Standard liveness/readiness pattern compatible with container orchestration. |
| Push-based instrumentation | Monitoring Layer ← every component | Metrics/traces/logs must be emitted at the point of occurrence, not reconstructed. |

## Responsibilities

- A new component or a materially new communication pattern between existing components requires an ADR per [09_Governance.md](09_Governance.md).
- Every port referenced in this document (`ConnectorPort`, `LLMProviderPort`, etc.) is a conceptual interface name for architectural communication purposes; exact method signatures are Deferred to Architecture-time implementation.

## Constraints

- This document does not define concrete class names, method signatures, or wire formats.
- Extraction-seam commentary describes architectural readiness, not a committed roadmap; sequencing is a planning-phase decision.

## Future Considerations

- As V1.0 usage data accumulates, the extraction-seam assessments here should be revisited against actual observed load and coupling, which may reorder the extraction candidates named per component.

## Acceptance Criteria

- [ ] All fifteen components from [30_System_Architecture.md](30_System_Architecture.md) have a stated internal structure, contract, communication pattern, and extraction-seam assessment.
- [ ] No component's description implies a specific database schema or API payload format.
- [ ] Plugin-readiness is explicitly addressed for the Connector Layer and AI Layer, consistent with the Extensibility principle.
