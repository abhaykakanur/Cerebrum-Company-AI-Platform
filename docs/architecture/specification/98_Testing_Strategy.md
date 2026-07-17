# 98 — Testing Strategy

## Purpose

This document defines Cerebrum's complete testing strategy: the nine-layer Testing Pyramid and the specific validation scope for each of its six most substantial layers (Unit, Integration, End-to-End, Performance, Security, AI Testing). It elaborates [32_Technology_Stack.md](32_Technology_Stack.md)'s testing tool selection (Pytest, Playwright, Vitest) and [61_AI_Evaluation.md](61_AI_Evaluation.md)'s AI evaluation methodology into a complete testing architecture.

## Scope

This document covers testing scope and methodology across all test types. It does not contain actual test code or test-case content, consistent with this phase's "do not write tests" constraint — it specifies *what* must be tested and *how thoroughly*, not the tests themselves.

## Definitions

- **Testing Pyramid** — A model organizing test types by volume and cost: many fast, cheap, narrow-scope tests (Unit) at the base, progressively fewer, slower, broader-scope tests (E2E, Performance) toward the top.
- **Determinism** (test context) — A test that produces the same pass/fail outcome on repeated runs against unchanged code, free of flakiness.

## Testing Pyramid

Cerebrum's testing strategy spans nine test types: Unit Tests, Integration Tests, API Tests, End-to-End Tests, Performance Tests, Load Tests, Security Tests, AI Evaluation Tests, Regression Tests.

| Test Type | Pyramid Position | Detailed In |
|---|---|---|
| Unit Tests | Base (highest volume, fastest) | This document, Unit Testing section |
| Integration Tests | Lower-middle | This document, Integration Testing section |
| API Tests | Middle — validates the API Domain contract ([80_API_Architecture.md](80_API_Architecture.md), [81_API_Standards.md](81_API_Standards.md)) independent of UI, sitting between Integration and End-to-End in scope | New — not separately detailed below given its direct correspondence to [81_API_Standards.md](81_API_Standards.md)'s already-specified contract |
| End-to-End Tests | Upper-middle | This document, End-to-End Testing section |
| Performance Tests | Upper (lower volume, higher cost) | This document, Performance Testing section |
| Load Tests | Upper — a Performance Testing variant specifically evaluating behavior under sustained/peak concurrent load, distinct from single-request latency measurement | Grouped with Performance Testing below |
| Security Tests | Cross-cutting, applied at multiple pyramid levels | This document, Security Testing section |
| AI Evaluation Tests | Cross-cutting, specific to the AI subsystem | This document, AI Testing section, extending [61_AI_Evaluation.md](61_AI_Evaluation.md) |
| Regression Tests | Cross-cutting — any test type re-run specifically to confirm a previously fixed defect has not reoccurred | Not a distinct test-writing methodology; a usage pattern applied across Unit/Integration/E2E tests, tagged and retained specifically for defects with a history of recurrence |

### Decision Rationale: Why Comprehensive Testing

A nine-layer testing strategy spanning this many types is justified — rather than being disproportionate to a Version 1.0 platform — because Cerebrum's core value proposition is trustworthiness: the AI Philosophy's grounding, citation, and hallucination-minimization commitments ([01_Product_Vision.md](01_Product_Vision.md)) are only as credible as the testing that verifies they actually hold. A platform whose central promise is "trustworthy organizational intelligence" cannot responsibly under-invest in verification relative to a platform with lower-stakes correctness requirements. AI Evaluation Tests and Security Tests in particular are not optional additions to a conventional testing pyramid — they are the direct verification mechanism for this specification's most safety-critical commitments (Part 5's AI Guardrails, Part 7's Threat Model).

## Unit Testing

Every business rule SHALL have unit tests. Unit tests SHALL mock external dependencies and exhibit fast execution and high determinism.

- **Scope:** Domain Layer business rules (entity invariants, domain services, specifications per [34_Architecture_Principles.md](34_Architecture_Principles.md)) and Application Layer use case orchestration logic — tested in isolation from Infrastructure Layer adapters.
- **Mocking external dependencies:** Every Repository port, LLM Provider port, and other Infrastructure-Layer-implemented interface is replaced with a test double in Unit Tests, per the Dependency Inversion pattern that makes this substitution possible without modifying the code under test.
- **Fast execution, high determinism:** Unit Tests must run in-memory, without network calls, database connections, or wall-clock-dependent behavior — a flaky or slow Unit Test undermines the fast-feedback-loop purpose the base of the Testing Pyramid exists to serve.

## Integration Testing

Integration Tests SHALL validate: Database, Search, Graph, Vector Store, Connectors, Queues, Workers, Authentication.

Each validates the specific Infrastructure Layer adapter for that concern against a real (typically containerized, per [95_DevOps_Architecture.md](95_DevOps_Architecture.md)'s Testing environment) instance of the underlying technology — PostgreSQL, OpenSearch, Neo4j, Qdrant, a mock/sandboxed Connector target, the Background Processing queue, Worker execution, and the Authentication Domain's credential/session mechanics — confirming the adapter correctly implements its domain-owned port contract against real, not mocked, infrastructure.

## End-to-End Testing

End-to-End Tests SHALL cover: Authentication, Search, Chat, Document Upload, Connector Sync, Knowledge Graph, Administration.

Each represents a complete user journey through the Frontend Layer and its full backend round-trip — using Playwright per [32_Technology_Stack.md](32_Technology_Stack.md) — verifying that a real user action (logging in, searching, chatting with the AI, uploading a document, triggering a connector sync, exploring the Knowledge Graph, performing an administrative task) succeeds end-to-end across every architectural layer this specification has defined, not merely that each layer works in isolation.

## Performance Testing

Performance Tests (including Load Tests) SHALL measure: Search Latency, Chat Latency, Connector Throughput, Worker Throughput, Database Performance, Memory Usage, CPU Usage, Concurrent Users.

Each metric is measured against the corresponding target already established in [39_Performance_Targets.md](39_Performance_Targets.md) (Part 3) and [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md) (Part 5) — Performance Testing's role is verification against those pre-established targets, not the origin of new targets. Concurrent Users testing specifically validates the Horizontal Scaling strategy ([39_Performance_Targets.md](39_Performance_Targets.md)) actually delivers the claimed scalability under real, simulated load rather than only in architectural theory.

## Security Testing

Security Testing SHALL perform: Dependency Scans, Secret Detection, Static Analysis, Authentication Testing, Authorization Testing, Permission Testing, Rate Limit Testing.

Each directly verifies a corresponding mitigation from [79_Threat_Model.md](79_Threat_Model.md): Dependency Scans and Secret Detection verify Credential Leakage mitigations; Static Analysis (security-focused) catches classes of Broken Authentication/Authorization defects before runtime; Authentication/Authorization/Permission Testing directly exercises the Unauthorized Access, Privilege Escalation, and Broken Authorization threat mitigations with adversarial test cases, not only happy-path verification; Rate Limit Testing verifies the API Abuse and Brute Force mitigations in [81_API_Standards.md](81_API_Standards.md) actually throttle as designed under simulated abuse. This is where the Threat Model's "no threat category left as only an aspirational statement" claim is operationally proven, not merely architecturally asserted.

## AI Testing

AI Evaluation Tests SHALL evaluate: Grounding Accuracy, Citation Accuracy, Hallucination Rate, Retrieval Precision, Retrieval Recall, Context Quality, Latency, Cost.

This directly extends [61_AI_Evaluation.md](61_AI_Evaluation.md)'s Automated Benchmark methodology into the CI/CD pipeline ([97_CICD_Architecture.md](97_CICD_Architecture.md)) — AI Evaluation Tests are the automated-benchmark portion of that document's evaluation methodology, run against the maintained, versioned test-query set, verifying that a Retrieval, Reasoning, or Prompt Construction change does not regress these eight metrics before it reaches Production. "Context Quality" is a new metric relative to [61_AI_Evaluation.md](61_AI_Evaluation.md)'s twelve — it measures whether Context Assembly ([54_Context_Assembly.md](54_Context_Assembly.md)) produced coherent, non-redundant, appropriately prioritized context, as a diagnostic signal distinct from but contributing to downstream Grounding Accuracy.

## Responsibilities

- Every new domain, use case, or AI capability introduced in a later phase must receive Unit Test coverage before merge, per the Test Coverage > 85% target in [103_Engineering_Guidelines.md](103_Engineering_Guidelines.md).
- AI Evaluation Tests must run on every change touching Retrieval, Reasoning, Prompt Construction, or Citation architecture, not only on a periodic schedule, given their regression-prevention role for this platform's most safety-critical guarantees.

## Constraints

- This document does not contain test code, test fixtures, or specific test-case enumerations — Deferred to Architecture/implementation.
- This document does not specify the exact E2E/Performance/AI Evaluation test triggering cadence within the CI/CD pipeline — see [97_CICD_Architecture.md](97_CICD_Architecture.md)'s open deferral on this point.

## Future Considerations

- As Regression Tests accumulate over time, a periodic review should prune tests for defects that have not recurred across many releases, balancing regression protection against Test Coverage maintenance burden.

## Acceptance Criteria

- [ ] All nine Testing Pyramid layers from the governing specification are defined and positioned.
- [ ] The Comprehensive Testing Decision Rationale is included, connecting testing investment to the AI Philosophy's trust commitments.
- [ ] Unit, Integration, End-to-End, Performance, Security, and AI Testing sections each address every item from the governing specification's respective list.
- [ ] AI Testing is explicitly connected to and extends, rather than duplicates, [61_AI_Evaluation.md](61_AI_Evaluation.md)'s existing methodology.
