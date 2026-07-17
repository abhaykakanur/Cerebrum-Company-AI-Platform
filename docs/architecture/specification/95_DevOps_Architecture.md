# 95 — DevOps Architecture

## Document Status

CES Version 1.0, Phase 0, Part 9. This document extends CES Phase 0 Parts 1–8 (documents 00–94) and does not rewrite them. It defines the Engineering Principles, Development Environments, Configuration Management, and Docker Strategy governing how Cerebrum is built and operated, elaborating [32_Technology_Stack.md](32_Technology_Stack.md)'s Deployment technology choices and [37_Configuration_Strategy.md](37_Configuration_Strategy.md)'s configuration architecture.

## Purpose

This document is the entry point into the Part 9 document set — the final operational layer covering how the fully-architected system from Parts 1–8 is built, tested, deployed, and run in production.

## Scope

This document covers engineering principles, environment strategy, configuration management (by cross-reference), and containerization strategy. It does not cover deployment topology (see [96_Deployment_Strategy.md](96_Deployment_Strategy.md)), CI/CD pipeline detail (see [97_CICD_Architecture.md](97_CICD_Architecture.md)), or testing (see [98_Testing_Strategy.md](98_Testing_Strategy.md)). No source code, Dockerfile, or CI/CD configuration appears in this document or any Part 9 document.

## Definitions

See [10_Glossary.md](10_Glossary.md). No new terms are introduced here.

## Engineering Principles

The codebase SHALL be: Readable, Modular, Well Documented, Strongly Typed, Self-Documenting, Consistently Structured, Testable, Observable, Secure, Maintainable.

Each of these ten qualities is already the direct consequence of principles established earlier in this specification, restated here as the binding engineering-culture standard:

| Quality | Primary Origin |
|---|---|
| Readable, Self-Documenting | [04_Project_Principles.md](04_Project_Principles.md)'s "Explicit over Implicit" |
| Modular | [34_Architecture_Principles.md](34_Architecture_Principles.md)'s Clean/Hexagonal Architecture |
| Well Documented | [100_Documentation_Standards.md](100_Documentation_Standards.md) |
| Strongly Typed | [99_Coding_Standards.md](99_Coding_Standards.md), [32_Technology_Stack.md](32_Technology_Stack.md)'s Pydantic/TypeScript choices |
| Consistently Structured | [33_Directory_Structure.md](33_Directory_Structure.md) |
| Testable | [98_Testing_Strategy.md](98_Testing_Strategy.md), enabled architecturally by Dependency Inversion ([34_Architecture_Principles.md](34_Architecture_Principles.md)) |
| Observable | [38_Observability.md](38_Observability.md), [101_Monitoring_Architecture.md](101_Monitoring_Architecture.md) |
| Secure | [75_Security_Architecture.md](75_Security_Architecture.md) |
| Maintainable | The governing outcome of every principle above, and of [04_Project_Principles.md](04_Project_Principles.md)'s "Maintainability over shortcuts" |

**Binding rule:** No "quick fixes" shall become permanent architecture. A shortcut taken under deadline pressure must be explicitly tracked (as a follow-up task, not a silent gap) and remediated — it may not simply persist uncorrected until it is mistaken for an intentional design decision. This directly extends [09_Governance.md](09_Governance.md)'s ADR discipline: a deliberate, reviewed exception to architecture is legitimate and documented; an unreviewed shortcut that quietly calcifies into de facto architecture is not.

## Development Environments

Cerebrum SHALL support four environments: Local Development, Testing, Staging, Production — each independently configurable per [37_Configuration_Strategy.md](37_Configuration_Strategy.md)'s Environment Variables and Configuration Files categories.

| Environment | Purpose | Typical Datastore Topology |
|---|---|---|
| Local Development | Individual developer iteration. | Docker Compose, per this document's Docker Strategy below. |
| Testing | Automated CI/CD test execution ([97_CICD_Architecture.md](97_CICD_Architecture.md), [98_Testing_Strategy.md](98_Testing_Strategy.md)). | Ephemeral, container-based, matching Local Development's topology for consistency. |
| Staging | Pre-production validation against production-like infrastructure. | Kubernetes-Ready deployment per [32_Technology_Stack.md](32_Technology_Stack.md), scaled down from Production. |
| Production | Live, customer-facing operation. | Kubernetes-Ready deployment at full scale, per [39_Performance_Targets.md](39_Performance_Targets.md)'s Scalability Strategy. |

**Independent configurability** means a configuration change in one environment (e.g., a Staging-only feature flag) never silently affects another — directly implementing [37_Configuration_Strategy.md](37_Configuration_Strategy.md)'s Configuration Precedence model, with "environment" as an implicit top-level scope above Organization/Workspace scoping.

## Configuration Management

Configuration SHALL be externalized, supporting Environment Variables, Configuration Files, Secrets, Feature Flags, and Runtime Configuration. This document does not re-architect configuration management — see [37_Configuration_Strategy.md](37_Configuration_Strategy.md) for the complete architecture, and [75_Security_Architecture.md](75_Security_Architecture.md) for Secrets Management specifically.

**Binding rule:** No secrets SHALL be committed to Git. This is enforced by the same Externalized Secrets Decision Rationale already established in [75_Security_Architecture.md](75_Security_Architecture.md), operationally reinforced here by [97_CICD_Architecture.md](97_CICD_Architecture.md)'s Security Scanning pipeline stage (Secret Detection), which specifically guards against this rule being violated by accident.

## Docker Strategy

**Development SHALL use Docker Compose.** Every major service SHALL have an isolated container: Frontend, Backend, PostgreSQL, Neo4j, Qdrant, Redis, MinIO, OpenSearch, Worker, Monitoring — directly matching the `deployment/docker/docker-compose.yml` stack already specified in [33_Directory_Structure.md](33_Directory_Structure.md).

**The architecture SHALL remain Kubernetes-ready** — restating [32_Technology_Stack.md](32_Technology_Stack.md)'s deployment target, with this document confirming that the Docker Compose-based Local Development topology and the Kubernetes-based Staging/Production topology use the same container images, differing only in orchestration, per [96_Deployment_Strategy.md](96_Deployment_Strategy.md).

### Decision Rationale: Why Docker Compose for Development

Docker Compose is chosen for Local Development because it directly delivers the Modular Monolith's "easier local development" rationale from [30_System_Architecture.md](30_System_Architecture.md): a single `docker-compose up` brings up the entire polyglot persistence stack (five datastores) plus the application services, without requiring a developer to install, configure, and version-match five separate database systems on their own machine, or to run a full Kubernetes cluster locally merely to iterate on application code.

### Decision Rationale: Why Kubernetes-Ready Architecture

Kubernetes-readiness is required despite Docker Compose sufficing for development because Production must satisfy the Horizontal Scaling, rolling deployment, and health-check-driven traffic routing requirements in [39_Performance_Targets.md](39_Performance_Targets.md) and [96_Deployment_Strategy.md](96_Deployment_Strategy.md) — Docker Compose has no native mechanism for these at production scale. The architecture achieves both by ensuring the application is built container-first and stateless at the process level (per [39_Performance_Targets.md](39_Performance_Targets.md)'s Horizontal Scaling strategy) from the start, so the same container images work under either orchestrator without an application redesign when moving from Local Development to Production.

## Responsibilities

- Every new service or datastore added in a later phase must receive its own isolated container in the Docker Compose stack before being considered development-ready.
- The "no quick fixes become permanent architecture" rule must be enforced in code review ([97_CICD_Architecture.md](97_CICD_Architecture.md)'s Code Review standards) — a PR introducing an undocumented shortcut should be flagged, not silently approved.

## Constraints

- This document does not contain Dockerfile content, docker-compose.yml syntax, or Kubernetes manifests — Deferred to Architecture, consistent with this phase's "do not write Dockerfiles" scope.
- This document does not specify exact resource limits, replica counts, or environment-specific scaling parameters — Deferred to Architecture/operations.

## Future Considerations

- As the team and codebase grow, the four-environment model may need a fifth "Preview" or "Ephemeral" environment class for per-PR preview deployments — a natural extension of the existing environment independence model, not a redesign.

## Acceptance Criteria

- [ ] All ten Engineering Principles from the governing specification are stated with their origin traced to existing specification content.
- [ ] The "no quick fixes" rule is stated as binding, connected to the ADR discipline in [09_Governance.md](09_Governance.md).
- [ ] All four Development Environments are defined with independent configurability addressed.
- [ ] Docker Strategy's ten containerized services are listed, with both Decision Rationales (Docker Compose, Kubernetes-Ready) included.
