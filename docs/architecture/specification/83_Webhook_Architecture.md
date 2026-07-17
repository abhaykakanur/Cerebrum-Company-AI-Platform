# 83 — Webhook Architecture

## Purpose

This document defines Cerebrum's outbound Webhook Architecture: the six event categories a webhook subscriber may register for, and the retry and signature verification mechanisms guaranteeing reliable, authentic delivery. It elaborates FR-AP-005 from [20_Functional_Requirements.md](20_Functional_Requirements.md).

## Scope

This document covers outbound webhook delivery. It does not cover inbound webhook receipt from source systems (the Connector Layer's Webhook Handler, see [65_Connector_Architecture.md](65_Connector_Architecture.md) component 9 and [68_Synchronization_Architecture.md](68_Synchronization_Architecture.md)'s Real-time Webhook Synchronization mode) — that is a distinct capability despite the shared "webhook" terminology: this document governs Cerebrum notifying external systems; the Connector Layer's Webhook Handler governs external systems notifying Cerebrum.

## Definitions

- **Webhook Subscription** — A registered endpoint and event-category filter an external system configures to receive Cerebrum-originated event notifications.
- **Signature Verification** — A cryptographic mechanism allowing a webhook recipient to confirm a received payload genuinely originated from Cerebrum and was not forged or tampered with in transit.

## Supported Event Categories

Webhooks SHALL support subscription to the following six event categories:

| Category | Example Events |
|---|---|
| Connector Events | Connector created, health status changed, authentication expired — sourced from [65_Connector_Architecture.md](65_Connector_Architecture.md) component 14 (Connector Event Publisher). |
| Synchronization Events | Sync started, sync completed, sync failed — directly extends FR-NT-003/FR-NT-004's Connector Failure Alerts and Sync Completion Notifications to external systems, not only Cerebrum's own Notification Domain. |
| Document Events | Document created, updated, deleted, archived — per [45_Data_Lifecycle.md](45_Data_Lifecycle.md)'s lifecycle stage transitions. |
| Knowledge Events | Knowledge Graph entity/relationship created or merged, Decision recorded — per FR-KG-001/002, FR-DI-001. |
| Administration Events | User invited/deactivated, role assigned, configuration changed — per [47_Data_Governance.md](47_Data_Governance.md)'s auditable-action list. |
| Audit Events | A subset of Audit Domain records an organization chooses to stream externally (e.g., to their own SIEM), respecting the same access-control sensitivity as direct Audit Domain access ([47_Data_Governance.md](47_Data_Governance.md), Open Question 37 in [27_Open_Questions.md](27_Open_Questions.md)). |

Every event category maps to domain events already raised internally per the Event-Driven-Ready pattern ([34_Architecture_Principles.md](34_Architecture_Principles.md)) — the Webhook Architecture is an external subscriber to the same event stream internal domains (Notification, Audit, Analytics) already consume, not a parallel event-generation mechanism.

## Retry

Webhook delivery SHALL be retried on failure, following the same Retry Engine pattern already established for Connector synchronization ([68_Synchronization_Architecture.md](68_Synchronization_Architecture.md)): exponential backoff, a defined retry limit, and Dead Letter Queue readiness for a subscription endpoint that fails delivery persistently (e.g., the subscriber's endpoint is down for an extended period) — a persistently failing webhook subscription is flagged to the subscribing organization's administrators (via the Notification Domain, in a deliberate cross-application of the same failure-visibility principle used for Connector Health) rather than silently retried forever or silently dropped.

## Signature Verification

Every outbound webhook payload SHALL be signed using a secret unique to the Webhook Subscription (managed via [75_Security_Architecture.md](75_Security_Architecture.md)'s Secrets Management, treating the webhook signing secret as an additional secret type alongside the seven already enumerated there). The receiving system verifies the signature before trusting the payload, preventing a forged request to the subscriber's endpoint from being mistaken for a genuine Cerebrum-originated event — this is the Replay Attack and API Abuse mitigation ([79_Threat_Model.md](79_Threat_Model.md)) specifically applied to the webhook delivery direction (protecting the *subscriber*, as opposed to Cerebrum's own API surfaces, which the Rate Limiting and Authentication mechanisms in [81_API_Standards.md](81_API_Standards.md) and [76_Authentication_Architecture.md](76_Authentication_Architecture.md) protect).

## Responsibilities

- Every new domain event type that should be externally subscribable must be mapped to one of the six event categories above before being exposed via webhook — an unmapped event type is not eligible for webhook delivery until this mapping is established.
- Signature Verification is mandatory for every Webhook Subscription without exception; there is no "unsigned webhook" option, consistent with Security by Default ([04_Project_Principles.md](04_Project_Principles.md)).

## Constraints

- This document does not specify the exact signature algorithm (e.g., HMAC-SHA256) or the retry backoff parameters — Deferred to Architecture.
- This document does not cover inbound webhook receipt — see [65_Connector_Architecture.md](65_Connector_Architecture.md) and [68_Synchronization_Architecture.md](68_Synchronization_Architecture.md) for that distinct capability.

## Future Considerations

- As webhook adoption grows, a webhook delivery dashboard (subscription health, delivery success rate, DLQ depth) should be added to the Administration Layer, mirroring the Connector Health visibility pattern already established.

## Acceptance Criteria

- [ ] All six webhook event categories from the governing specification are defined and traced to their originating domain event source.
- [ ] Retry is defined consistently with the existing Retry Engine pattern from [68_Synchronization_Architecture.md](68_Synchronization_Architecture.md), not as a separate, divergent mechanism.
- [ ] Signature Verification is defined as mandatory, with its threat-mitigation purpose explicit.
- [ ] The distinction between this document's outbound webhooks and the Connector Layer's inbound webhook handling is explicit, preventing terminology confusion.
