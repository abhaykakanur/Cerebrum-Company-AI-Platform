# 23 — Use Case Catalog

## Purpose

This document maps each of the 20 primary use cases defined in [06_Use_Cases.md](06_Use_Cases.md) to the functional requirements in [20_Functional_Requirements.md](20_Functional_Requirements.md) that fulfill it. It demonstrates that every use case is realizable by the current requirement set and gives later phases a way to verify that no use case has been left unsupported.

## Scope

This document covers use-case-to-requirement mapping only. It does not restate use case descriptions (see [06_Use_Cases.md](06_Use_Cases.md)) or requirement detail (see [20_Functional_Requirements.md](20_Functional_Requirements.md)).

## Definitions

See [10_Glossary.md](10_Glossary.md) for "Use Case." No new terms are introduced here.

## Use Case to Requirement Mapping

### UC-01: Find company knowledge
**Primary requirements:** FR-ES-001, FR-ES-002, FR-ES-003, FR-ES-010, FR-AUTZ-003
**Supporting requirements:** FR-KG-006, FR-ES-007

### UC-02: Search documentation
**Primary requirements:** FR-ES-001 through FR-ES-004, FR-KP-001
**Supporting requirements:** FR-DM-002, FR-CN-011 (Confluence, Notion, SharePoint categories)

### UC-03: Search code
**Primary requirements:** FR-ES-001, FR-ES-003, FR-CN-011 (GitHub, GitLab categories)
**Supporting requirements:** FR-KP-001, FR-KG-001 (code-referenced entities)

### UC-04: Search tickets
**Primary requirements:** FR-ES-004, FR-CN-011 (Jira, Linear categories)
**Supporting requirements:** FR-KP-006, FR-ES-005

### UC-05: Search architecture decisions
**Primary requirements:** FR-DI-001, FR-EM-003, FR-ES-001
**Supporting requirements:** FR-DI-003, FR-CT-001

### UC-06: Search meeting summaries
**Primary requirements:** FR-MI-003, FR-EM-006, FR-ES-001
**Supporting requirements:** FR-MI-001, FR-CT-001

### UC-07: Locate experts
**Primary requirements:** FR-ED-001, FR-ED-002, FR-ED-005
**Supporting requirements:** FR-KG-001, FR-UM-008

### UC-08: Understand historical decisions
**Primary requirements:** FR-DI-001, FR-DI-002, FR-DI-003
**Supporting requirements:** FR-EM-002, FR-KG-007

### UC-09: Understand project evolution
**Primary requirements:** FR-EM-004, FR-KG-007, FR-DI-002
**Supporting requirements:** FR-KS-003, FR-KG-005

### UC-10: Find dependencies
**Primary requirements:** FR-KG-006, FR-ES-006, FR-ED-003
**Supporting requirements:** FR-KG-002, FR-EM-004

### UC-11: Generate knowledge summaries
**Primary requirements:** FR-AR-002, FR-AR-001, FR-MI-003
**Supporting requirements:** FR-CT-001, FR-RT-002

### UC-12: Visualize relationships
**Primary requirements:** FR-KG-008, FR-KG-006
**Supporting requirements:** FR-KG-001, FR-KG-002

### UC-13: Understand organizational history
**Primary requirements:** FR-EM-002, FR-EM-005, FR-KG-007
**Supporting requirements:** FR-DI-002, FR-KS-003

### UC-14: Retrieve institutional knowledge
**Primary requirements:** FR-EM-005, FR-ED-004
**Supporting requirements:** FR-UM-004, FR-UM-006 (post-departure access continuity)

### UC-15: Support employee onboarding
**Primary requirements:** FR-EM-004, FR-ED-001, FR-CV-001
**Supporting requirements:** FR-EM-005, FR-ES-001

### UC-16: Support incident investigations
**Primary requirements:** FR-AR-003, FR-EM-006, FR-KG-006
**Supporting requirements:** FR-DI-006, FR-ES-004

### UC-17: Support architecture reviews
**Primary requirements:** FR-EM-003, FR-DI-005, FR-DI-002
**Supporting requirements:** FR-KG-006, FR-CT-001

### UC-18: Support compliance audits
**Primary requirements:** FR-AU-001, FR-AU-006, FR-CT-002
**Supporting requirements:** FR-AU-002, FR-AU-005

### UC-19: Support technical discovery
**Primary requirements:** FR-ES-001, FR-KG-006, FR-AR-003
**Supporting requirements:** FR-EM-003, FR-ED-001

### UC-20: Support enterprise research
**Primary requirements:** FR-AR-002, FR-AR-003, FR-AR-004
**Supporting requirements:** FR-RT-001, FR-CT-001, FR-CF-001

## Coverage Summary

| Use Case | Requirements Domains Involved | Fully Covered? |
|---|---|---|
| UC-01–UC-04 | Enterprise Search, Knowledge Processing, Connector | Yes |
| UC-05, UC-08, UC-17 | Decision Intelligence, Enterprise Memory, Citation | Yes |
| UC-06, UC-16 | Meeting Intelligence, Enterprise Memory | Yes |
| UC-07, UC-14 | Expertise Discovery, Knowledge Graph, User Management | Yes |
| UC-09, UC-13 | Enterprise Memory, Knowledge Graph, Knowledge Storage | Yes |
| UC-10, UC-12 | Knowledge Graph, Enterprise Search | Yes |
| UC-11, UC-19, UC-20 | AI Reasoning, Retrieval, Citation | Yes |
| UC-15 | Enterprise Memory, Expertise Discovery, Conversation | Yes |
| UC-18 | Audit, Citation | Yes |

Every primary use case in [06_Use_Cases.md](06_Use_Cases.md) maps to at least one Critical- or High-priority requirement. No use case is currently unsupported by the requirement set in [20_Functional_Requirements.md](20_Functional_Requirements.md).

## Responsibilities

- Any new use case added to [06_Use_Cases.md](06_Use_Cases.md) after this phase must have a corresponding mapping added here, and any resulting requirement gap must be raised as a new entry in [20_Functional_Requirements.md](20_Functional_Requirements.md) rather than left implicit.
- Any requirement in [20_Functional_Requirements.md](20_Functional_Requirements.md) that maps to no use case here should be reviewed for continued relevance — it may indicate scope not actually grounded in a stated user need.

## Constraints

- "Primary requirements" denotes the smallest set of requirements without which the use case could not function at all. "Supporting requirements" materially improve the use case but are not strictly load-bearing for a minimal version of it.
- This document does not assign delivery priority or sequencing across use cases; that is a planning-phase decision.

## Future Considerations

- As new connector categories or domains are added per [12_Future_Expansion.md](12_Future_Expansion.md), this mapping should be revisited for use cases that would benefit from the new coverage (e.g., a new connector expanding UC-02's source coverage).

## Acceptance Criteria

- [ ] All 20 use cases from [06_Use_Cases.md](06_Use_Cases.md) are mapped.
- [ ] Every mapped requirement ID exists in [20_Functional_Requirements.md](20_Functional_Requirements.md) / [22_Requirement_Catalog.md](22_Requirement_Catalog.md).
- [ ] No use case maps to zero requirements.
