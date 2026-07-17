# 27 — Open Questions (CES Phase 0, Part 2)

## Purpose

This document records ambiguities and "Deferred to Architecture" points surfaced while writing the complete functional requirements in [20_Functional_Requirements.md](20_Functional_Requirements.md). It extends, and does not replace, [11_Open_Questions.md](11_Open_Questions.md) from CES Phase 0 Part 1. Per project instruction, ambiguity is recorded here rather than resolved by assumption.

## Scope

This document covers ambiguities specific to functional requirement detail — points where a requirement's acceptance criteria intentionally stopped short of specifying an implementation choice. It does not restate the Part 1 open questions; where a Part 2 question is a direct refinement of a Part 1 question, it is cross-referenced rather than duplicated. Numbering continues from [11_Open_Questions.md](11_Open_Questions.md) to maintain a single, unified backlog.

## Definitions

See [10_Glossary.md](10_Glossary.md). No new terms are introduced here.

## Open Questions

| # | Question | Why It Is Open | Related Requirement(s) | Blocks |
|---|---|---|---|---|
| 18 | What is the complete built-in role catalog beyond the minimum of Administrator, Member, and Viewer-equivalent access levels? | FR-AUTZ-001 establishes that built-in roles must exist but defers the complete catalog to architecture. Directly extends Open Question 2 in [11_Open_Questions.md](11_Open_Questions.md). | FR-AUTZ-001, FR-AUTZ-004 | Authorization architecture, Administration Domain UI design. |
| 19 | When a user is denied access to a resource, does the system reveal that the resource exists (e.g., "access denied") or hide its existence entirely (e.g., a generic not-found response)? | FR-AUTZ-003 and FR-ES-010 require permission enforcement but explicitly defer the leakage policy, since the correct answer may depend on matching each source system's own visibility model. | FR-AUTZ-003, FR-ES-010, FR-CT-002 | Search and retrieval architecture, API error-response design. |
| 20 | What is the default and configurable conflict-resolution strategy when a connector reports ambiguous or conflicting source-system state (e.g., most-recent-write-wins vs. manual review for all conflicts)? | FR-CN-008 requires deterministic resolution but does not specify the default strategy. | FR-CN-008 | Connector framework architecture. |
| 21 | Which of the 23 named connector categories ship in the initial general-availability release versus a later wave? | FR-CN-011 requires eventual support for all 23 categories but explicitly defers sequencing to roadmap planning. | FR-CN-011 | Release planning, engineering roadmap. |
| 22 | What is the maximum chunk size for content chunking, and does it vary by the AI model or embedding model in use? | FR-KP-005 requires a defined maximum but notes it is model-dependent and therefore an architecture-time decision. | FR-KP-005, FR-KP-009 | Knowledge Processing architecture, AI model selection (Open Question 10 in [11_Open_Questions.md](11_Open_Questions.md)). |
| 23 | When the embedding model changes, how does the system manage the transition so that search remains available throughout re-embedding (e.g., dual-write, shadow index, hard cutover)? | FR-KP-009 requires that searchability not be lost during re-embedding but defers the cutover mechanism. | FR-KP-009 | Knowledge Processing and Enterprise Search architecture. |
| 24 | What specific, quantifiable threshold defines "below the quality bar" for knowledge quality validation, and does it vary by content type? | FR-KP-010 requires a quality bar to exist and be enforced but does not quantify it. | FR-KP-010, FR-EM-009 | Knowledge Processing architecture, quality-analytics baseline (FR-AL-003). |
| 25 | What confidence threshold, if any, triggers automatic (rather than human-reviewed) merging of likely-duplicate graph entities? | FR-KG-003 and FR-KG-004 support both manual and automatic merge paths but do not specify where the line falls. | FR-KG-003, FR-KG-004 | Knowledge Graph architecture. |
| 26 | What is the default hybrid search weighting between keyword and semantic relevance signals, and is it globally fixed or tunable per workspace? | FR-ES-003 requires configurability but not a default. | FR-ES-003, FR-CG-002 | Enterprise Search architecture. |
| 27 | Are autocomplete suggestions (FR-ES-007) drawn from permission-filtered content per requesting user, or from an aggregated, permission-agnostic query-pattern index? | The requirement flags this as an open implementation choice with a direct bearing on whether suggestions could ever leak information about content a user cannot see. | FR-ES-007 | Enterprise Search architecture, Security Domain review. |
| 28 | What is the maximum reasoning-context token budget, and does it vary per AI model provider or per query type? | FR-RT-005 requires enforcement of a budget but defers the specific limit, which depends on model sourcing (Open Question 10 in [11_Open_Questions.md](11_Open_Questions.md)). | FR-RT-005, FR-AR-004 | Retrieval and AI Reasoning architecture, AI vendor strategy. |
| 29 | Is there a maximum depth or breadth limit on query decomposition and cross-document reasoning to bound cost and latency for very broad research queries? | FR-AR-003 and FR-AR-004 support multi-hop, multi-document reasoning without a stated bound. | FR-AR-003, FR-AR-004 | AI Reasoning architecture, cost/latency modeling. |
| 30 | By what methodology is hallucination-control effectiveness (FR-AR-006) independently tested and measured on an ongoing basis? | The requirement mandates the control but defers the test methodology, which materially affects how confidently the AI Philosophy commitment can be claimed as met. | FR-AR-006, FR-AL-003 | AI Reasoning quality assurance process. |
| 31 | What configuration surface allows an organization to choose between "show low-confidence answers with a warning" versus "withhold low-confidence answers entirely," and can this be set per query category (e.g., stricter for compliance questions)? | FR-CF-003 requires the capability to exist but defers the configuration mechanism and granularity. | FR-CF-003, FR-CG-001 | Confidence Domain and Configuration Domain architecture. |
| 32 | What security review process governs the future introduction of external (outside-organization) document sharing links, given the elevated risk of a permission bypass? | FR-DM-006's Future Expansion explicitly flags this capability as requiring dedicated review before being built, rather than being treated as a routine extension. | FR-DM-006 | Document Management architecture, Security Domain sign-off. |
| 33 | Does Cerebrum perform its own audio/video transcription for meeting intelligence, or does it exclusively ingest transcripts produced by external tools? | Directly restates and sharpens Open Question 12 in [11_Open_Questions.md](11_Open_Questions.md) in light of FR-MI-001's dependency on transcript availability. | FR-MI-001, FR-MI-002 | Meeting Intelligence architecture, connector/ingestion scope. |
| 34 | What is the required remediation SLA for known dependency and infrastructure vulnerabilities, and does it vary by severity? | FR-SC-005 requires tracked remediation but defers the specific SLA. | FR-SC-005 | Security operations process, compliance posture (Open Question 11 in [11_Open_Questions.md](11_Open_Questions.md)). |
| 35 | What is the defined customer-notification policy and timeline following a confirmed security incident, and how does it vary by applicable jurisdiction? | FR-SC-006 requires a policy to exist but defers its content, which is likely to be jurisdiction-dependent. | FR-SC-006 | Security incident response process, legal/compliance review. |
| 36 | What is the standard deprecation window between a breaking API change shipping in a new version and the prior version being retired? | FR-AP-006 requires a defined window but does not set it. | FR-AP-006 | API Domain architecture, partner/integration communication process. |
| 37 | What justification and approval workflow governs an administrator's access to search-history audit data, given the surveillance-adjacent sensitivity of query-level logging? | FR-AU-005 flags this as requiring a defined, audited justification mechanism beyond ordinary administrative access. | FR-AU-005 | Audit Domain architecture, internal privacy policy. |

## Responsibilities

- No later-phase document may silently resolve one of these questions through an implementation choice. Each must be closed via an ADR per [09_Governance.md](09_Governance.md), with this document and the corresponding requirement in [20_Functional_Requirements.md](20_Functional_Requirements.md) updated to reflect the resolution.
- Where a Part 2 question and a Part 1 question ([11_Open_Questions.md](11_Open_Questions.md)) are closely related, resolving one should trigger a review of the other for consistency.

## Constraints

- This list reflects ambiguities identifiable from the Part 2 document set as currently written; it is not exhaustive of every future architecture-time decision.
- Every "Deferred to Architecture" marker in [20_Functional_Requirements.md](20_Functional_Requirements.md) that carries genuine ambiguity (as opposed to routine, low-risk implementation latitude) should have a corresponding entry here; not every "Deferred to Architecture" marker rises to the level of an open question requiring governance resolution before proceeding.

## Future Considerations

- As each question is resolved, move its row to a "Resolved Questions" section (to be added, mirroring the structure anticipated in [11_Open_Questions.md](11_Open_Questions.md)) with a link to the governing ADR.
- Architecture-phase kickoff should treat unresolved questions that block foundational domains (Authorization, Connector, Security) as hard prerequisites, not parallelizable work.

## Acceptance Criteria

- [ ] Every question is phrased so it can be answered with a concrete decision, not left as open-ended discussion.
- [ ] Every question cites the specific requirement ID(s) it blocks.
- [ ] No question duplicates a question already recorded in [11_Open_Questions.md](11_Open_Questions.md) without adding requirement-level specificity.
