# 38 — Observability and Error Handling

## Purpose

This document defines Cerebrum's observability architecture (structured logging, metrics, distributed tracing, health/readiness/liveness checks, performance monitoring) and its enterprise error-handling strategy (error taxonomy and handling rules by category). Both are cross-cutting concerns owned architecturally by the Monitoring Layer and `core/errors/` (see [33_Directory_Structure.md](33_Directory_Structure.md)) and consumed by every domain.

## Scope

This document covers the *architecture* of observability and error handling — what is emitted, in what shape, and how errors are categorized and propagated. It does not define specific dashboards, alert thresholds, or log retention periods, which are Deferred to Architecture-time operational configuration.

## Definitions

- **Structured Log** — A log entry emitted as a machine-parseable record (key-value fields), not free-text.
- **Metric** — A numeric measurement emitted at a point in time, aggregated over a window (counter, gauge, histogram).
- **Trace** — A record of a request's path through the system, composed of nested spans.
- **Liveness Check** — A signal that a process is running and not deadlocked; failure triggers a restart.
- **Readiness Check** — A signal that a process is able to serve traffic; failure removes it from load-balancer rotation without restarting it.

## Structured Logging

- Every log entry SHALL be emitted via the Structlog-based shared instrumentation port (see [32_Technology_Stack.md](32_Technology_Stack.md), [34_Architecture_Principles.md](34_Architecture_Principles.md)), never via a bare `print` or unstructured string.
- Every log entry SHALL include, at minimum: timestamp, log level, originating domain/component, and a correlation identifier (see Distributed Tracing below) linking it to the request or background Task that produced it.
- Fields identified as secrets (per [37_Configuration_Strategy.md](37_Configuration_Strategy.md)) SHALL be redacted by the logging adapter automatically, based on a field-name denylist and a value-pattern check (Deferred to Architecture for the specific redaction ruleset) — never relying solely on developer discipline to avoid logging a secret.
- Audit-relevant log entries additionally satisfy the Audit Domain's `AuditRecord` structure (FR-AU-001) — audit logging is a distinct, append-only, non-deletable stream layered on top of, not identical to, general application logging.

## Metrics

- Every component emits metrics via the Prometheus-compatible instrumentation port, categorized as:
  - **Counters** — monotonically increasing counts (e.g., requests served, connector sync failures).
  - **Gauges** — current-value measurements (e.g., active DLQ depth, active sessions).
  - **Histograms** — distributions (e.g., search latency, retrieval latency), required wherever a percentile-based Performance Target exists (see [39_Performance_Targets.md](39_Performance_Targets.md)).
- Metric names and labels follow a consistent `<component>_<domain>_<measurement>` convention (e.g., `retrieval_layer_context_assembly_duration_seconds`) so Analytics Layer and Monitoring Layer queries remain predictable as new domains are added.
- The Authorization Layer's `checkPermission`/`filterByPermission` calls are explicitly instrumented given their high call frequency (per [31_Component_Architecture.md](31_Component_Architecture.md)'s performance concern), since a latency regression there compounds across every permission-scoped request.

## Distributed Tracing

- Every inbound request (API Domain) and every Background Processing Task SHALL originate or propagate an OpenTelemetry trace context, carried through every in-process domain call and into every outbound infrastructure adapter call (database query, LLM provider call, connector external call).
- The AI Layer's multi-step reasoning pipeline (decompose → retrieve → assemble → generate → validate → cite → score) SHALL be instrumented as a chain of nested spans within one trace, directly enabling the Reasoning Transparency requirement (FR-AR-008) to be fulfilled by inspecting the trace, not by bespoke logging.
- Trace context propagates across the async boundary into Background Processing Tasks (e.g., a connector sync triggered by a user action carries the originating trace ID), so an ingestion failure can be traced back to its triggering request even though it executed asynchronously.

## Health Checks

Three distinct check types, per standard container-orchestration practice, map onto the Monitoring Domain's `getHealthStatus` port (FR-MN-001):

| Check Type | Question Answered | Failure Response |
|---|---|---|
| **Liveness** | Is this process running and not deadlocked? | Orchestrator restarts the process. |
| **Readiness** | Can this process currently serve traffic (are its dependencies — database, cache, search index — reachable)? | Orchestrator removes it from load-balancer rotation without restarting. |
| **Health (detailed)** | What is the status of each subsystem this process depends on? | Surfaced to the Monitoring Layer dashboard (FR-MN-004); does not directly trigger an orchestrator action. |

Every one of the fifteen high-level components in [30_System_Architecture.md](30_System_Architecture.md) that has an external dependency (a datastore, an LLM provider, an external connector target) contributes to the detailed Health check's aggregate status.

## Performance Monitoring

- Every request-path operation with a stated target in [39_Performance_Targets.md](39_Performance_Targets.md) (search response, knowledge retrieval, chat first-token) emits a histogram metric covering its full duration, broken down by pipeline stage where the operation spans multiple domains (e.g., Retrieval's context assembly duration is measured separately from AI Reasoning's generation duration, even though both contribute to the end-to-end Chat Response First Token target).
- Performance regressions are surfaced through the Monitoring Layer's degradation alerting (FR-MN-003), using the percentile distributions this section requires, not averages alone, consistent with FR-AL-005's acceptance criteria.

## Error Handling Strategy

### Error Taxonomy

Every error in Cerebrum SHALL be classified into exactly one of the following categories at the point it is raised, using a shared `core/errors/` type hierarchy (see [33_Directory_Structure.md](33_Directory_Structure.md)) rather than raw framework exceptions propagating uncaught:

| Category | Definition | Example | Handling |
|---|---|---|---|
| **Validation Error** | Input fails structural or business-rule validation before any state change is attempted. | A DTO missing a required field; an FR-WS-003 invariant violation ("cannot remove the last owner"). | Returned to the caller immediately with a specific, actionable message; never retried automatically. |
| **Security Error** | An authentication or authorization check fails, or a security invariant (e.g., tenant isolation) would be violated. | FR-AUTZ-003 permission denial; FR-SC-004 cross-tenant access attempt. | Returned to the caller as a denial (with leakage policy per Open Question 19 in [40_Open_Questions.md](40_Open_Questions.md)); always logged to the Audit Domain regardless of leakage policy. |
| **Connector Error** | A failure interacting with an external source system. | Rate limit, expired credential, unreachable endpoint. | Classified transient vs. non-transient per [36_Background_Processing.md](36_Background_Processing.md)'s retry policy; surfaces to FR-CN-006 health status. |
| **AI Error** | A failure in the retrieval or reasoning pipeline. | LLM provider timeout, embedding provider failure, response validation failure (FR-AR-005). | A provider-level failure is retried against the same or a fallback provider (Deferred to Architecture for fallback policy); a validation failure produces an explicit low-confidence/unknown response (FR-AR-006), never a silently degraded answer. |
| **Storage Error** | A failure reading from or writing to a datastore. | Connection failure, constraint violation, integrity check failure (FR-KS-007). | Recoverable storage errors (e.g., transient connection loss) are retried with backoff; constraint violations are treated as Validation Errors at the domain boundary that allowed the invalid state to be attempted. |
| **Search Error** | A failure executing a search or retrieval query. | Search index unreachable, malformed query after validation (indicating a defect, not user input). | Degrades gracefully where possible (e.g., fall back from hybrid to keyword-only search) rather than failing the entire request outright; degraded-mode responses are flagged as such, consistent with Explainability. |

### Recoverable vs. Fatal

- **Recoverable errors** are errors the system can retry, degrade gracefully from, or route to a Dead Letter Queue for later handling without halting an otherwise-healthy request or Task stream (most Connector, AI-provider, and transient Storage errors).
- **Fatal errors** indicate the current request or Task cannot proceed and must fail immediately and visibly rather than being retried or masked (most Validation and Security errors — retrying a permission denial does not change the outcome and must not be attempted).
- The distinction is made explicitly at the point an error is raised (via the error type hierarchy), not inferred later by a generic catch-all handler — this directly supports Explicit over Implicit from [04_Project_Principles.md](04_Project_Principles.md).

### Error Propagation Rule

An error crossing a domain boundary (e.g., from Knowledge Storage to Knowledge Processing) is never silently swallowed and re-raised as a generic exception — it is either handled at the boundary (with the handling action itself logged) or propagated as its original typed error, preserving the category information every downstream handler (including the AI Layer's user-facing error messaging and the Monitoring Layer's alerting) depends on.

## Responsibilities

- Every new component or domain added in a later phase must emit logs, metrics, and traces through the shared instrumentation port — bespoke, uninstrumented code paths are a review-blocking finding.
- Every new error condition identified during implementation must be classified into the taxonomy above before release; an unclassified error defaulting to "Fatal" is the safe default pending classification, never "Recoverable" by default.

## Constraints

- This document does not specify exact log retention periods, metric cardinality limits, or trace sampling rates — Deferred to Architecture-time operational configuration.
- This document does not define the specific error-response HTTP status codes or payload shape returned by the API Domain — Deferred to Architecture.

## Future Considerations

- As the system scales, trace sampling (rather than 100% capture) will likely become necessary for cost reasons; the sampling strategy should preserve 100% capture for Security Errors and AI Reasoning traces given their audit/explainability importance, even if general request traces are sampled.

## Acceptance Criteria

- [ ] Structured logging, metrics, distributed tracing, and all three health-check types (liveness, readiness, detailed health) are architecturally defined.
- [ ] The error taxonomy covers all eight categories named in the governing specification (recoverable, fatal, validation, security, connector, AI, storage, search).
- [ ] Every error category states its handling rule, not just its definition.
- [ ] Observability is connected to specific, traceable requirements (FR-MN-001–004, FR-AL-005, FR-AR-008) rather than described in the abstract.
