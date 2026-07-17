# 93 — Notification Architecture

## Purpose

This document defines the frontend Notification experience and its seven notification types, mapping each to the Notification Domain architecture already established in [35_Domain_Architecture.md](35_Domain_Architecture.md) and FR-NT-001 through FR-NT-005 (Part 2).

## Scope

This document covers the frontend presentation of notifications. It does not redefine the Notification Domain's backend architecture, delivery mechanics, or data model — see [35_Domain_Architecture.md](35_Domain_Architecture.md) and [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md)'s Notification entity.

## Definitions

- **Toast** — A transient, auto-dismissing notification surfaced at the moment of an event.
- **Persistent Notification** — A notification retained in the Notification Center until explicitly dismissed or acted upon.

## Notification Types

| Type | Presentation | Backend Mapping |
|---|---|---|
| In-app | Rendered within the Notification Center component ([87_Component_Library.md](87_Component_Library.md)). | FR-NT-001 |
| Toast | Rendered via the Toast component, auto-dismissing per [85_Frontend_Architecture.md](85_Frontend_Architecture.md)'s Microinteractions timing. | FR-NT-001, real-time delivery variant |
| Persistent | Rendered via the Notification Center, remaining until dismissed. | FR-NT-001, distinguished from Toast by retention behavior |
| Connector Alerts | Toast or Persistent, depending on severity — a Connector Failure Alert (FR-NT-003) warrants Persistent treatment given its actionable, non-transient nature. | FR-NT-003 |
| Sync Complete | Toast, typically low-urgency and appropriately transient. | FR-NT-004 |
| Failures | Persistent, given their actionable nature — mirrors Connector Alerts' treatment. | [38_Observability.md](38_Observability.md)'s error taxonomy, surfaced per FR-KP-010's quality-flagging pattern where applicable (e.g., FR-NT-005's quality-failure notification) |
| Admin Notices | Persistent, scoped to users holding relevant Administration permissions ([77_Authorization_Model.md](77_Authorization_Model.md)). | New — platform- or organization-level announcements, not tied to a single FR-NT requirement but consistent with the Notification Domain's general architecture |

## Toast vs. Persistent: Governing Rule

The distinction between Toast and Persistent presentation is not cosmetic — it reflects whether a notification requires user action or acknowledgment (Persistent) versus purely informational, time-bound awareness (Toast). A notification whose underlying event is one of [47_Data_Governance.md](47_Data_Governance.md)'s auditable, security-, or operationally-significant actions (Connector Failure, Permission Change-adjacent Admin Notices) defaults to Persistent; routine, expected-outcome events (Sync Complete on a healthy connector) default to Toast. This mapping is Deferred to Architecture for exhaustive per-event-type assignment but the governing principle above is binding.

## Responsibilities

- Every new notification-triggering event introduced in a later phase must be classified as Toast or Persistent per the governing rule above before being wired into the frontend.
- The Notification Center must respect the same permission-scoping as every other UI surface — a notification about another user's action is visible only where the requesting user's Authorization Layer permissions ([77_Authorization_Model.md](77_Authorization_Model.md)) would also permit visibility into that underlying action.

## Constraints

- This document does not redefine the Notification Domain's delivery/persistence backend architecture — see [35_Domain_Architecture.md](35_Domain_Architecture.md).
- This document does not specify exact Toast auto-dismiss timing beyond the general <250ms transition rule (which governs the Toast's appear/disappear animation, not its on-screen dwell time, which is a separate, Deferred-to-Architecture parameter).

## Future Considerations

- As notification volume grows, the Notification Center may warrant grouping/digest behavior (e.g., "5 documents processed" rather than 5 separate entries) — a presentation-layer enhancement building on, not replacing, the underlying per-event Notification entities.

## Acceptance Criteria

- [ ] All seven notification types from the governing specification are defined with presentation treatment and backend mapping.
- [ ] The Toast-vs-Persistent governing rule is stated explicitly, not left as an arbitrary per-type assignment.
- [ ] Permission-scoping of notification visibility is addressed, consistent with the Thin Frontend and Authorization principles established elsewhere.
