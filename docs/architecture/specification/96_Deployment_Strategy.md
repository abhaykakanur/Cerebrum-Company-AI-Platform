# 96 — Deployment Strategy

## Purpose

This document defines the seven deployment models Cerebrum supports, from local single-machine deployment through future Kubernetes orchestration, and the update-delivery strategies (Blue-Green, Rolling Updates) the architecture is designed to support.

## Scope

This document covers deployment topology options. It does not cover CI/CD pipeline mechanics that produce deployable artifacts (see [97_CICD_Architecture.md](97_CICD_Architecture.md)) or the containerization strategy those deployments run on (see [95_DevOps_Architecture.md](95_DevOps_Architecture.md)'s Docker Strategy).

## Definitions

- **Blue-Green Deployment** — A release strategy running two identical production environments ("blue" and "green"), directing live traffic to one while the other receives the new release, then switching traffic atomically once the new release is validated.
- **Rolling Update** — A release strategy incrementally replacing old-version instances with new-version instances, a few at a time, avoiding a full-environment cutover.

## Supported Deployment Models

| Model | Description | Primary Use |
|---|---|---|
| Local Deployment | Docker Compose-based, per [95_DevOps_Architecture.md](95_DevOps_Architecture.md). | Individual development, demos, evaluation. |
| Cloud Deployment | Deployment to a managed cloud environment (specific provider Deferred to Architecture per Open Question 65 in [40_Open_Questions.md](40_Open_Questions.md)). | Production and Staging, primary target. |
| Single VM Deployment | The full stack (or a scaled-down subset) running on one virtual machine, without container orchestration. | Small-scale evaluation deployments, or organizations with strict infrastructure-minimization requirements; explicitly not the primary scaling path. |
| Container Deployment | Docker Compose or an equivalent container runtime, without full Kubernetes orchestration. | Mid-scale deployments not yet requiring Kubernetes's operational complexity, consistent with the Modular Monolith's "prove value before paying complexity cost" philosophy applied to deployment, not only application architecture. |
| Future Kubernetes Deployment | Full Kubernetes orchestration, per [32_Technology_Stack.md](32_Technology_Stack.md)'s Kubernetes-Ready target. | Large-scale, multi-tenant Production deployment requiring Horizontal Scaling ([39_Performance_Targets.md](39_Performance_Targets.md)). |
| Blue-Green Ready | See definition above — the architecture supports this pattern once Kubernetes (or an equivalent orchestrator) is in use. | Zero-downtime major releases, schema-migration-sensitive deployments. |
| Rolling Updates Ready | See definition above. | Routine, frequent releases where full environment duplication (Blue-Green) is unnecessary overhead. |

## Deployment Model Progression

These seven models are not independent alternatives chosen once and fixed — they represent a progression matching Cerebrum's own scale, mirroring the Modular-Monolith-to-microservices extraction philosophy in [31_Component_Architecture.md](31_Component_Architecture.md): an organization or Cerebrum's own SaaS operation may begin with Container Deployment and graduate to Future Kubernetes Deployment as scale demands, without an application redesign, because the underlying container images and the Stateless API principle ([80_API_Architecture.md](80_API_Architecture.md)) are identical across every model.

## Blue-Green and Rolling Update Readiness

Both patterns depend on architectural properties already established elsewhere in this specification, not new mechanisms this document introduces:

- **Statelessness** ([80_API_Architecture.md](80_API_Architecture.md)) — a request can be served by any instance, old or new version, without session-affinity concerns, which both Blue-Green and Rolling Updates require.
- **Backward-compatible database migrations** — a Rolling Update runs old and new application code against the same database simultaneously during the transition window, requiring every schema migration to be backward-compatible for at least one release cycle (Deferred to Architecture for the specific migration discipline, tracked in [104_Open_Questions.md](104_Open_Questions.md)).
- **Health-check-driven traffic routing** ([38_Observability.md](38_Observability.md)'s Readiness checks) — both patterns rely on the orchestrator only routing traffic to instances that report Ready, preventing a not-yet-warmed-up new instance from receiving traffic prematurely.

## Responsibilities

- Every schema migration or breaking API change proposed in a later phase must be evaluated for Rolling Update compatibility (per the backward-compatible migration requirement above) before merge — an incompatible migration requires either a Blue-Green deployment for that release or a multi-step, backward-compatible migration sequence.
- Deployment model selection for a specific customer or Cerebrum's own SaaS operation is an operational/business decision informed by, but not dictated by, this document's progression — smaller deployments are not required to jump straight to Kubernetes.

## Constraints

- This document does not specify a target cloud provider — Deferred to Architecture, per Open Question 65 in [40_Open_Questions.md](40_Open_Questions.md).
- This document does not specify Kubernetes manifest structure or Helm/Kustomize usage — Deferred to Architecture, per Open Question 46 in [40_Open_Questions.md](40_Open_Questions.md).

## Future Considerations

- As Future Kubernetes Deployment moves from "future" to delivered, this document should be updated to reflect the specific orchestration tooling chosen, converting the "Future" qualifier to a confirmed, current deployment model.

## Acceptance Criteria

- [ ] All seven deployment models from the governing specification are defined.
- [ ] Blue-Green and Rolling Update readiness are connected to specific, already-established architectural properties (statelessness, health checks, migration compatibility) rather than presented as independent new mechanisms.
- [ ] The deployment models are framed as a scale-matched progression, consistent with the Modular Monolith's extraction philosophy already established in Part 3.
