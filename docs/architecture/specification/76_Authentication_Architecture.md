# 76 — Authentication Architecture

## Purpose

This document defines the complete Authentication Service architecture: supported authentication methods, Session Management, Token Strategy, and Password Policy. It elaborates FR-AUTH-001 through FR-AUTH-009 from [20_Functional_Requirements.md](20_Functional_Requirements.md) and the Authentication Domain architecture from [35_Domain_Architecture.md](35_Domain_Architecture.md).

## Scope

This document covers authentication mechanics. It does not cover authorization/permission modeling (see [77_Authorization_Model.md](77_Authorization_Model.md)) or the broader security subsystem (see [75_Security_Architecture.md](75_Security_Architecture.md)).

## Definitions

See [10_Glossary.md](10_Glossary.md) and [35_Domain_Architecture.md](35_Domain_Architecture.md)'s Authentication Domain entry. No new terms are introduced here.

## Supported Authentication Methods

| Method | Status | Requirement Traceability |
|---|---|---|
| Email + Password | Supported | FR-AUTH-001 |
| OAuth 2.0 | Supported | FR-AUTH-004 |
| OpenID Connect | Supported | Extends FR-AUTH-004/005 — OIDC is the identity layer typically paired with OAuth 2.0 for SSO. |
| Magic Link | Supported (future) | FR-AUTH-003; "future" here aligns with the general roadmap-sequencing pattern already established (Open Question 21, [27_Open_Questions.md](27_Open_Questions.md)), not a change to FR-AUTH-003's status as a defined requirement. |
| Enterprise SSO | Ready | FR-AUTH-005 |
| SAML | Ready | FR-AUTH-005's future-readiness scope |
| Azure AD | Ready | A specific SSO/OAuth provider readiness target, consistent with FR-AUTH-004/005's provider-agnostic port design |
| Google Workspace | Ready | Same pattern as Azure AD |
| Multi-Factor Authentication | Ready | FR-AUTH-006 |
| Device Session Tracking | Supported | FR-AUTH-008 |
| Refresh Tokens | Supported | See Token Strategy below |
| Session Revocation | Supported | FR-AUTH-007 |

"Ready" (as distinct from "Supported") denotes the same architectural readiness pattern already established in Part 2 for FR-AUTH-004/005/006 — the port-based design accommodates the capability without core redesign, but specific protocol/provider implementation is Deferred to Architecture.

## Session Management

Every Session SHALL track the following ten fields, extending FR-AUTH-007 and the `Session` entity in [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md):

Session ID, User, Device, Browser, Operating System, IP Address, Created Time, Last Activity, Expiration, Revocation Status.

This field set is what makes FR-AUTH-007's "a user can view a list of their active sessions with device/location metadata" acceptance criterion concretely deliverable — Device, Browser, Operating System, and IP Address are the specific fields that metadata comprises.

## Token Strategy

Support the following seven capabilities:

| Capability | Description |
|---|---|
| Access Token | Short-lived, used for per-request authentication. |
| Refresh Token | Longer-lived, used to obtain a new Access Token without re-authenticating. |
| Token Rotation | A Refresh Token is single-use; using it issues a new Refresh Token alongside a new Access Token, invalidating the prior Refresh Token — this limits the blast radius of a leaked Refresh Token to a single use. |
| Token Expiration | Both token types carry a defined expiration, per FR-AUTH-007's session lifetime pattern. |
| Token Revocation | Per FR-AUTH-007's session revocation, extended to tokens specifically — revoking a session invalidates its associated Access and Refresh Tokens. |
| Secure Storage | Tokens are never logged (per [38_Observability.md](38_Observability.md)'s secret-redaction requirement, applied to tokens as sensitive values) and are transmitted only over encrypted channels ([75_Security_Architecture.md](75_Security_Architecture.md)'s Encryption in Transit). |
| Token Validation | Every request's Access Token is validated (signature, expiration, revocation status) by the Authentication Layer middleware before any downstream domain logic executes. |

### Decision Rationale: Why JWT-Based Authentication

JWT (JSON Web Tokens) was selected in [32_Technology_Stack.md](32_Technology_Stack.md) for Access Tokens specifically because it is stateless and self-contained — the Authentication Layer can validate a token's signature and claims without a database round-trip on every request, directly supporting the Search Response and Chat Response First Token performance targets ([39_Performance_Targets.md](39_Performance_Targets.md)), which cannot tolerate a synchronous session-store lookup on every permission-scoped call given the Authorization Layer's own high call-frequency performance concern ([31_Component_Architecture.md](31_Component_Architecture.md)). This statelessness is deliberately balanced against revocability via short Access Token lifetimes combined with a stateful, database-backed Refresh Token and Session record — the JWT itself cannot be individually revoked before expiration, but its short lifetime bounds the exposure window, while Session revocation (FR-AUTH-007) prevents the Refresh Token from minting further Access Tokens. This hybrid design is why both a stateless token (JWT Access Token) and a stateful record (Session, Refresh Token) coexist in this architecture rather than choosing one exclusively.

## Password Policy

Support the following seven configurable password policy elements, extending FR-AUTH-001's baseline with administrator-configurable granularity:

| Element | Description |
|---|---|
| Minimum Length | The shortest permitted password. |
| Maximum Length | The longest permitted password (bounding, not merely permitting, to avoid denial-of-service via extremely long input to hashing functions). |
| Complexity | Character-class requirements (uppercase, lowercase, digit, symbol), where an organization chooses to enforce them. |
| Reuse Prevention | Preventing a user from reusing a recent prior password. |
| Expiration | Whether and how often a password must be changed, where an organization's policy requires it. |
| History | How many prior passwords are retained (hashed, never plaintext) for Reuse Prevention comparison. |
| Reset Policy | The specific mechanics governing FR-AUTH-002's password reset flow at an organization-configurable level (e.g., reset link expiration duration). |

Password Policy settings are Configuration Domain-owned ([62_AI_Governance.md](62_AI_Governance.md)'s pattern applied to security settings, not AI settings specifically — see [37_Configuration_Strategy.md](37_Configuration_Strategy.md)), organization-scoped per FR-OR-003's inheritance model.

## Responsibilities

- Every new authentication method added in a later phase must integrate with the existing Session and Token architecture above, not introduce a parallel session/token model.
- Password Policy defaults must balance security and usability; a later phase setting an unreasonably restrictive default (e.g., mandatory 24-hour expiration) without organizational opt-in would work against adoption goals in [02_Project_Goals.md](02_Project_Goals.md).

## Constraints

- This document does not specify exact token lifetimes, password policy default values, or specific SSO protocol implementation detail — Deferred to Architecture.
- MFA factor types (TOTP, hardware key, SMS) are not committed to here — see FR-AUTH-006's existing "Deferred to Architecture" scope.

## Future Considerations

- As passwordless authentication (Magic Link) matures from "future" to delivered status, Password Policy's relevance narrows for organizations that disable password login entirely, consistent with FR-AUTH-001's Future Expansion note.

## Acceptance Criteria

- [ ] All twelve supported authentication methods from the governing specification are listed with their support status.
- [ ] All ten Session Management fields from the governing specification are defined.
- [ ] All seven Token Strategy capabilities from the governing specification are defined, with the JWT Decision Rationale included.
- [ ] All seven Password Policy elements from the governing specification are defined as configurable.
