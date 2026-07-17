# 103 — Engineering Guidelines

## Purpose

This document defines the six engineering-level Performance Targets closing out Part 9's scope, and synthesizes the eight engineering-workflow qualities named in this Part's Objective (Reliability, Maintainability, Observability, Automation, Code Quality, Developer Productivity, Scalability, Reproducibility) against the documents that deliver each — serving as this Part's capstone, connecting DevOps, CI/CD, Testing, Coding, Documentation, and Monitoring/Backup standards into one coherent engineering practice.

## Scope

This document covers engineering-level performance targets and the synthesis of Part 9's workflow qualities. It does not introduce new architecture — every element here traces to a document already established in documents 95–102 or earlier parts.

## Definitions

See [10_Glossary.md](10_Glossary.md). No new terms are introduced here.

## Performance Targets

| Target | Value | Relationship to Prior Parts |
|---|---|---|
| API Availability | > 99.9% | Directly restates the System Availability target from [39_Performance_Targets.md](39_Performance_Targets.md), applied specifically to the API Domain surface. |
| Search Latency | < 2s | Directly restates [39_Performance_Targets.md](39_Performance_Targets.md)'s Search Response target. |
| Chat First Token | < 3s | Directly restates [39_Performance_Targets.md](39_Performance_Targets.md)'s Chat Response First Token target, matching [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md)'s Time to First Token stage target. |
| Connector Success Rate | > 99% | Directly restates [39_Performance_Targets.md](39_Performance_Targets.md)'s Connector Sync Reliability target. |
| Worker Success Rate | > 99% | New — the Background Processing Layer analog to Connector Success Rate, applied across all nine Workers ([91_Background_Processing.md](91_Background_Processing.md)), tracked via Job Record outcomes ([92_Queue_Architecture.md](92_Queue_Architecture.md)). |
| Test Coverage | > 85% | New — the quantitative target underpinning [98_Testing_Strategy.md](98_Testing_Strategy.md)'s Unit Testing requirement that "every business rule shall have unit tests," giving that qualitative requirement a measurable, CI/CD-enforceable ([97_CICD_Architecture.md](97_CICD_Architecture.md)) threshold. |

These six targets are the engineering-organization-facing restatement of targets already established (four of six) or new operational targets (two of six: Worker Success Rate, Test Coverage) completing the measurement picture across every layer this CES has architected — from infrastructure (API Availability) through application behavior (Search/Chat Latency, Connector/Worker Success) to code quality (Test Coverage).

## Synthesis: The Eight Engineering Workflow Qualities

Part 9's Objective named eight qualities the engineering process shall emphasize. Each is delivered by a specific combination of documents 95–102, not by any single one in isolation:

| Quality | Primary Delivering Documents |
|---|---|
| Reliability | [98_Testing_Strategy.md](98_Testing_Strategy.md) (comprehensive testing), [102_Backup_Recovery.md](102_Backup_Recovery.md) (data durability), [96_Deployment_Strategy.md](96_Deployment_Strategy.md) (Blue-Green/Rolling Update readiness) |
| Maintainability | [99_Coding_Standards.md](99_Coding_Standards.md), [100_Documentation_Standards.md](100_Documentation_Standards.md), and by extension [34_Architecture_Principles.md](34_Architecture_Principles.md) (Part 3) |
| Observability | [101_Monitoring_Architecture.md](101_Monitoring_Architecture.md), extending [38_Observability.md](38_Observability.md) (Part 3) |
| Automation | [97_CICD_Architecture.md](97_CICD_Architecture.md)'s thirteen-stage pipeline |
| Code Quality | [99_Coding_Standards.md](99_Coding_Standards.md)'s tooling and "no lint warnings" rule |
| Developer Productivity | [95_DevOps_Architecture.md](95_DevOps_Architecture.md)'s Docker Compose rationale, [97_CICD_Architecture.md](97_CICD_Architecture.md)'s fast-feedback-first pipeline ordering |
| Scalability | [96_Deployment_Strategy.md](96_Deployment_Strategy.md)'s Kubernetes-Ready progression, extending [39_Performance_Targets.md](39_Performance_Targets.md) (Part 3) |
| Reproducibility | [95_DevOps_Architecture.md](95_DevOps_Architecture.md)'s environment independence, [97_CICD_Architecture.md](97_CICD_Architecture.md)'s deterministic Artifact Generation |

No quality here is delivered by aspiration alone — each traces to a specific, binding mechanism already specified across this document set, consistent with this entire CES's governing discipline of connecting every principle to its concrete enforcement.

## Closing Principle: Engineering Practice as Trust Infrastructure

The engineering practices across documents 95–103 are not administrative overhead layered on top of "the real work" of building Cerebrum — they are the mechanism by which every trust-critical commitment made earlier in this specification (grounding, citation, permission correctness, tenant isolation, hallucination minimization) remains true in the shipped product rather than only in the architecture document describing it. A CI/CD pipeline that skips Security Scanning, a Coding Standard routinely waived under deadline pressure, or a Backup Strategy never actually restore-tested each represent a point where this specification's promises could silently diverge from reality. Part 9 exists to close that gap.

## Responsibilities

- Every one of the six Performance Targets must be continuously monitored per [101_Monitoring_Architecture.md](101_Monitoring_Architecture.md), with a sustained miss treated as an engineering-priority incident, not a background statistic.
- Any proposal to weaken a Part 9 standard (skip a CI/CD stage, lower Test Coverage, relax a Coding Standard) for expediency requires an ADR per [09_Governance.md](09_Governance.md), explicitly weighed against this document's Closing Principle.

## Constraints

- This document does not introduce new architecture beyond synthesizing documents 95–102 — any apparent new requirement here should be treated as a cross-reference error to correct, not a new binding rule.

## Future Considerations

- As Cerebrum's engineering organization grows, this document's eight-quality synthesis should be revisited periodically to confirm the delivering documents still accurately reflect practice, not only original intent.

## Acceptance Criteria

- [ ] All six Performance Targets from the governing specification are defined and reconciled with prior parts' targets where applicable.
- [ ] All eight engineering workflow qualities from the governing specification's Objective are synthesized with their delivering documents identified.
- [ ] The Closing Principle connects Part 9's operational discipline back to this CES's trust-critical commitments from Parts 1 and 5, not left as a generic engineering-best-practices statement.
