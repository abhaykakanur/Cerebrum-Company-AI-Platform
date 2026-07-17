# 100 — Documentation Standards

## Purpose

This document defines the seven required sections every module's documentation SHALL contain, and the eight artifact types maintained at the engineering-organization level (ADRs, API documentation, and related references). It ensures the documentation discipline this CES itself models is carried forward into implementation-phase code documentation.

## Scope

This document covers documentation structure and required artifact types. It does not contain actual documentation content for any specific module — Deferred to Architecture/implementation.

## Definitions

- **Module** — A cohesive unit of code, typically corresponding to one domain's `domain/`, `application/`, or `infrastructure/` package ([33_Directory_Structure.md](33_Directory_Structure.md)), or a Connector Plugin ([66_Connector_SDK.md](66_Connector_SDK.md)).

## Module Documentation Requirements

Every module SHALL contain a README covering the following seven sections:

| Section | Content |
|---|---|
| README | The entry point — what the module does, in one or two sentences, and links to the sections below. |
| Architecture Overview | How the module is internally structured, referencing [34_Architecture_Principles.md](34_Architecture_Principles.md)'s layering pattern as applied to this specific module. |
| Public Interfaces | The module's exposed ports/application services, per [35_Domain_Architecture.md](35_Domain_Architecture.md)'s per-domain Public Interfaces field — this documentation should stay synchronized with that specification document, not diverge from it. |
| Dependencies | What this module depends on, per [35_Domain_Architecture.md](35_Domain_Architecture.md)'s per-domain Dependencies field. |
| Configuration | Any module-specific configuration, per [37_Configuration_Strategy.md](37_Configuration_Strategy.md)'s categories. |
| Usage | How another module or a developer invokes this module's capability, with illustrative (not exhaustive) examples. |
| Limitations | Known constraints, edge cases not yet handled, or deliberate scope exclusions — directly extending this CES's own "Constraints" section pattern (every CES document includes one) down to the code-documentation level. |

This seven-section structure directly mirrors the section pattern this very CES document set already uses (Purpose/Scope/Definitions/.../Constraints/Future Considerations/Acceptance Criteria) — module documentation is the implementation-phase continuation of the same documentation discipline established across Parts 1–9, not a new, unrelated standard.

## Engineering Documentation

Beyond per-module documentation, the engineering organization SHALL maintain the following eight artifact types:

| Artifact | Purpose | Relationship to This CES |
|---|---|---|
| Architecture Decision Records (ADRs) | Records of significant decisions, per [09_Governance.md](09_Governance.md)'s governance process. | The primary mechanism by which this CES evolves post-Phase-0. |
| API Documentation | Complete, current documentation for every API surface, per [80_API_Architecture.md](80_API_Architecture.md)'s "Documented" principle. | Generated from or kept synchronized with the actual API Domain implementation. |
| Database Documentation | Schema documentation for PostgreSQL, Neo4j, Qdrant. | Traces back to [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md)'s logical model. |
| Connector Documentation | Per-connector integration detail (authentication flow, scope, known limitations), per [65_Connector_Architecture.md](65_Connector_Architecture.md)'s catalog. | One document per connector in the catalog, extending that document's category-level detail to connector-specific implementation notes. |
| Deployment Guide | How to deploy Cerebrum across the models in [96_Deployment_Strategy.md](96_Deployment_Strategy.md). | Operational elaboration of that document. |
| Runbooks | Step-by-step procedures for operational scenarios (a connector outage, a degraded search index, a failed deployment). | Operational elaboration of [79_Threat_Model.md](79_Threat_Model.md) and [38_Observability.md](38_Observability.md)'s failure-handling architecture. |
| Troubleshooting Guide | Common issues and their diagnosis/resolution paths, organized around [38_Observability.md](38_Observability.md)'s error taxonomy. | Practical companion to the error taxonomy's abstract categories. |
| Developer Guide | Onboarding documentation for engineers joining the project — how to set up Local Development ([95_DevOps_Architecture.md](95_DevOps_Architecture.md)), the Coding Standards ([99_Coding_Standards.md](99_Coding_Standards.md)), and the overall codebase orientation. | The practical, day-one-usable digest of this entire CES, not a replacement for it. |

## Responsibilities

- Every new module introduced in a later phase must ship with all seven README sections before being considered complete — an undocumented module is equivalent to an untested one in review severity, per [98_Testing_Strategy.md](98_Testing_Strategy.md)'s Coverage requirements.
- Documentation must be kept synchronized with the code and specification it describes — a Public Interfaces section describing a capability the module no longer provides is a defect, not a stale-but-harmless artifact, since it actively misleads future maintainers.

## Constraints

- This document does not specify a documentation authoring tool or format (Markdown, a wiki, generated API docs) beyond assuming Markdown consistency with this CES's own format — Deferred to Architecture.
- This document does not mandate documentation review as a distinct CI/CD pipeline stage — it is expected to be verified as part of the existing Code Review process ([97_CICD_Architecture.md](97_CICD_Architecture.md)).

## Future Considerations

- As the Connector catalog grows (per [65_Connector_Architecture.md](65_Connector_Architecture.md)), Connector Documentation should be evaluated for a templated, semi-automated generation process given its high per-connector volume and structural similarity across connectors.

## Acceptance Criteria

- [ ] All seven Module Documentation sections from the governing specification are defined.
- [ ] All eight Engineering Documentation artifact types from the governing specification are defined and connected to their originating CES document.
- [ ] The module documentation structure is explicitly connected to this CES's own document-section pattern, reinforcing documentation as a continuous discipline rather than a phase-0-only practice.
