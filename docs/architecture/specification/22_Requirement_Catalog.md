# 22 — Requirement Catalog

## Purpose

This document is a flat, sortable index of every functional requirement defined in [20_Functional_Requirements.md](20_Functional_Requirements.md). It exists for quick lookup, coverage checking, and reporting — consult the source document for full requirement detail (description, acceptance criteria, dependencies, future expansion).

## Scope

This catalog lists Requirement ID, Title, Domain, and Priority only. It duplicates no descriptive content from [20_Functional_Requirements.md](20_Functional_Requirements.md).

## Definitions

See [10_Glossary.md](10_Glossary.md) and the Priority Definitions in [20_Functional_Requirements.md](20_Functional_Requirements.md).

## Priority Summary

| Priority | Count |
|---|---|
| Critical | 79 |
| High | 61 |
| Medium | 51 |
| Low | 9 |
| **Total** | **200** |

## Catalog by Domain

### 1. Identity (ID)
| ID | Title | Priority |
|---|---|---|
| FR-ID-001 | Organization Creation | Critical |
| FR-ID-002 | Workspace Creation | Critical |
| FR-ID-003 | Organization Profile Management | Medium |
| FR-ID-004 | Workspace Profile Management | Medium |
| FR-ID-005 | Organization Branding | Low |

### 2. Workspace (WS)
| ID | Title | Priority |
|---|---|---|
| FR-WS-001 | Workspace Lifecycle Management | Critical |
| FR-WS-002 | Workspace Configuration | High |
| FR-WS-003 | Workspace Ownership | Critical |
| FR-WS-004 | Workspace Transfer | Medium |
| FR-WS-005 | Workspace Deletion | High |
| FR-WS-006 | Workspace Archival | Medium |

### 3. Organization (OR)
| ID | Title | Priority |
|---|---|---|
| FR-OR-001 | Organization Lifecycle Management | Critical |
| FR-OR-002 | Multi-Workspace Organization Structure | Critical |
| FR-OR-003 | Organization-Level Settings Inheritance | High |

### 4. User Management (UM)
| ID | Title | Priority |
|---|---|---|
| FR-UM-001 | User Registration | Critical |
| FR-UM-002 | User Invitation | Critical |
| FR-UM-003 | User Activation | High |
| FR-UM-004 | User Deactivation | Critical |
| FR-UM-005 | User Suspension | Medium |
| FR-UM-006 | User Soft Delete | High |
| FR-UM-007 | User Profile and Preferences Management | Medium |
| FR-UM-008 | Organizational Relationship Metadata | Medium |

### 5. Authentication (AUTH)
| ID | Title | Priority |
|---|---|---|
| FR-AUTH-001 | Email and Password Authentication | Critical |
| FR-AUTH-002 | Password Reset | Critical |
| FR-AUTH-003 | Magic Link Authentication | Medium |
| FR-AUTH-004 | OAuth Readiness | High |
| FR-AUTH-005 | SSO Readiness | High |
| FR-AUTH-006 | MFA Readiness | High |
| FR-AUTH-007 | Session Management | Critical |
| FR-AUTH-008 | Device Management and Remember Device | Low |
| FR-AUTH-009 | Account Recovery | Medium |

### 6. Authorization (AUTZ)
| ID | Title | Priority |
|---|---|---|
| FR-AUTZ-001 | Role-Based Access Control | Critical |
| FR-AUTZ-002 | Permission Inheritance | Critical |
| FR-AUTZ-003 | Resource-Scoped Permissions | Critical |
| FR-AUTZ-004 | Administrative Permission Tiers | High |
| FR-AUTZ-005 | Least-Privilege Default Enforcement | Critical |
| FR-AUTZ-006 | Permission Change Auditing | Critical |

### 7. Connector (CN)
| ID | Title | Priority |
|---|---|---|
| FR-CN-001 | Connector Authentication Framework | Critical |
| FR-CN-002 | Connection Validation | Critical |
| FR-CN-003 | Full Sync | Critical |
| FR-CN-004 | Incremental Sync | Critical |
| FR-CN-005 | Sync Scheduling and Manual Trigger | High |
| FR-CN-006 | Connector Health Monitoring | High |
| FR-CN-007 | Retry and Failure Handling | High |
| FR-CN-008 | Sync Conflict Handling | Medium |
| FR-CN-009 | Connector Activity Logging | High |
| FR-CN-010 | Connector Metadata Extraction | Critical |
| FR-CN-011 | Supported Connector Catalog | High |
| FR-CN-012 | Connector Extensibility Framework | Critical |

### 8. Knowledge Ingestion (KI)
| ID | Title | Priority |
|---|---|---|
| FR-KI-001 | Manual Document Upload | Critical |
| FR-KI-002 | Bulk and Folder Upload | High |
| FR-KI-003 | Connector-Sourced Ingestion | Critical |
| FR-KI-004 | Scheduled and Incremental Ingestion | Critical |
| FR-KI-005 | Duplicate Detection | High |
| FR-KI-006 | Version Detection | High |
| FR-KI-007 | Ingestion Metadata Extraction | Critical |
| FR-KI-008 | Language Detection | Medium |
| FR-KI-009 | OCR Trigger | High |
| FR-KI-010 | Content Normalization | Critical |
| FR-KI-011 | Ingestion Failure Recovery | High |
| FR-KI-012 | Ingestion Reporting | Medium |

### 9. Knowledge Processing (KP)
| ID | Title | Priority |
|---|---|---|
| FR-KP-001 | Text Extraction | Critical |
| FR-KP-002 | Image and Table Extraction | High |
| FR-KP-003 | OCR Processing | High |
| FR-KP-004 | Language Normalization | Medium |
| FR-KP-005 | Content Chunking | Critical |
| FR-KP-006 | Metadata Enrichment | High |
| FR-KP-007 | Keyword and Topic Extraction | High |
| FR-KP-008 | Entity and Relationship Extraction | Critical |
| FR-KP-009 | Embedding Generation | Critical |
| FR-KP-010 | Knowledge Quality Validation | High |

### 10. Knowledge Storage (KS)
| ID | Title | Priority |
|---|---|---|
| FR-KS-001 | Persistent Content Storage | Critical |
| FR-KS-002 | Metadata Storage | Critical |
| FR-KS-003 | Version History Retention | Critical |
| FR-KS-004 | Retention Policy Enforcement | High |
| FR-KS-005 | Archival and Restore | Medium |
| FR-KS-006 | Delete and Soft Delete | Critical |
| FR-KS-007 | Storage Integrity Verification | Medium |

### 11. Knowledge Graph (KG)
| ID | Title | Priority |
|---|---|---|
| FR-KG-001 | Entity Creation | Critical |
| FR-KG-002 | Relationship Creation | Critical |
| FR-KG-003 | Entity and Relationship Merging | High |
| FR-KG-004 | Duplicate Entity Resolution | High |
| FR-KG-005 | Graph Versioning | Medium |
| FR-KG-006 | Graph Traversal | Critical |
| FR-KG-007 | Entity and Relationship Timeline | Medium |
| FR-KG-008 | Graph Visualization Data Support | Medium |

### 12. Enterprise Search (ES)
| ID | Title | Priority |
|---|---|---|
| FR-ES-001 | Keyword Search | Critical |
| FR-ES-002 | Semantic Search | Critical |
| FR-ES-003 | Hybrid Search | Critical |
| FR-ES-004 | Metadata and Filtered Search | High |
| FR-ES-005 | Faceted Search | Medium |
| FR-ES-006 | Graph-Based Search | Medium |
| FR-ES-007 | Autocomplete and Suggestions | Medium |
| FR-ES-008 | Search Result Ranking | Critical |
| FR-ES-009 | Result Explanation | High |
| FR-ES-010 | Permission-Aware Search Enforcement | Critical |

### 13. Retrieval (RT)
| ID | Title | Priority |
|---|---|---|
| FR-RT-001 | Hybrid Retrieval | Critical |
| FR-RT-002 | Context Assembly | Critical |
| FR-RT-003 | Source Ranking | High |
| FR-RT-004 | Context Deduplication and Optimization | High |
| FR-RT-005 | Token Budgeting | Critical |
| FR-RT-006 | Citation Preservation Through Retrieval | Critical |
| FR-RT-007 | Context Validation | High |

### 14. AI Reasoning (AR)
| ID | Title | Priority |
|---|---|---|
| FR-AR-001 | Grounded Answer Generation | Critical |
| FR-AR-002 | Evidence Synthesis | Critical |
| FR-AR-003 | Cross-Document Reasoning | High |
| FR-AR-004 | Query Decomposition | High |
| FR-AR-005 | Response Validation | Critical |
| FR-AR-006 | Hallucination Reduction Controls | Critical |
| FR-AR-007 | Structured Answer Output | Medium |
| FR-AR-008 | Reasoning Transparency | High |

### 15. Enterprise Memory (EM)
| ID | Title | Priority |
|---|---|---|
| FR-EM-001 | Conversation Memory | High |
| FR-EM-002 | Decision Memory | Critical |
| FR-EM-003 | Architecture Memory | High |
| FR-EM-004 | Project Memory | High |
| FR-EM-005 | Employee and Institutional Memory | Critical |
| FR-EM-006 | Meeting Memory | High |
| FR-EM-007 | Customer Memory | Medium |
| FR-EM-008 | Policy Memory | High |
| FR-EM-009 | Knowledge Aging and Staleness Detection | High |
| FR-EM-010 | Memory Freshness Signals | Medium |

### 16. Conversation (CV)
| ID | Title | Priority |
|---|---|---|
| FR-CV-001 | Conversational Query Submission | Critical |
| FR-CV-002 | Multi-Turn Context Retention | High |
| FR-CV-003 | Conversation History | Medium |
| FR-CV-004 | Conversation Export | Low |
| FR-CV-005 | Follow-Up Question Handling | Low |

### 17. Citation (CT)
| ID | Title | Priority |
|---|---|---|
| FR-CT-001 | Citation Attachment | Critical |
| FR-CT-002 | Citation Source Linking | Critical |
| FR-CT-003 | Citation Verification | Critical |
| FR-CT-004 | Missing-Citation Disclosure | Critical |

### 18. Confidence (CF)
| ID | Title | Priority |
|---|---|---|
| FR-CF-001 | Confidence Scoring | Critical |
| FR-CF-002 | Confidence Display | Critical |
| FR-CF-003 | Low-Confidence Handling | Critical |
| FR-CF-004 | Confidence Calibration Feedback Loop | Medium |

### 19. Document Management (DM)
| ID | Title | Priority |
|---|---|---|
| FR-DM-001 | Document Download | High |
| FR-DM-002 | Document Preview | High |
| FR-DM-003 | Document Version History | Medium |
| FR-DM-004 | Tagging and Classification | Medium |
| FR-DM-005 | Collections and Folders | Medium |
| FR-DM-006 | Document Sharing | Medium |
| FR-DM-007 | Document Archiving | Medium |

### 20. Meeting Intelligence (MI)
| ID | Title | Priority |
|---|---|---|
| FR-MI-001 | Transcript Ingestion | High |
| FR-MI-002 | Speaker Identification Readiness | Medium |
| FR-MI-003 | Meeting Summarization | High |
| FR-MI-004 | Action Item Extraction | High |
| FR-MI-005 | Decision Extraction from Meetings | High |
| FR-MI-006 | Follow-Up Generation | Low |
| FR-MI-007 | Meeting Knowledge Linking | Medium |

### 21. Decision Intelligence (DI)
| ID | Title | Priority |
|---|---|---|
| FR-DI-001 | Decision Recording | Critical |
| FR-DI-002 | Decision Timeline | High |
| FR-DI-003 | Decision Reasoning Capture | Critical |
| FR-DI-004 | Decision Participants | High |
| FR-DI-005 | Evidence Linking | Medium |
| FR-DI-006 | Outcome Tracking | Medium |

### 22. Expertise Discovery (ED)
| ID | Title | Priority |
|---|---|---|
| FR-ED-001 | Expert Identification | High |
| FR-ED-002 | Skill and Technology Mapping | Medium |
| FR-ED-003 | Project Mapping | Medium |
| FR-ED-004 | Knowledge Ownership Attribution | Medium |
| FR-ED-005 | Availability Metadata | Low |

### 23. Analytics (AL)
| ID | Title | Priority |
|---|---|---|
| FR-AL-001 | Search Analytics | Medium |
| FR-AL-002 | Usage Analytics | Medium |
| FR-AL-003 | Knowledge Coverage Analytics | High |
| FR-AL-004 | Connector Analytics | Medium |
| FR-AL-005 | Performance Analytics | Medium |
| FR-AL-006 | Adoption Analytics | Low |

### 24. Administration (AD)
| ID | Title | Priority |
|---|---|---|
| FR-AD-001 | Workspace Administration | Critical |
| FR-AD-002 | User Administration | Critical |
| FR-AD-003 | Connector Administration | Critical |
| FR-AD-004 | Administrative Delegation | Medium |

### 25. Monitoring (MN)
| ID | Title | Priority |
|---|---|---|
| FR-MN-001 | System Health Monitoring | Critical |
| FR-MN-002 | Ingestion and Processing Monitoring | High |
| FR-MN-003 | Alerting on Degradation | High |
| FR-MN-004 | Uptime Dashboard | Medium |

### 26. Audit (AU)
| ID | Title | Priority |
|---|---|---|
| FR-AU-001 | Audit Log Capture | Critical |
| FR-AU-002 | Permission Change Audit Trail | Critical |
| FR-AU-003 | Login History | Critical |
| FR-AU-004 | Connector Activity History | High |
| FR-AU-005 | Search History Audit | Medium |
| FR-AU-006 | Administrative Action History | Critical |

### 27. Configuration (CG)
| ID | Title | Priority |
|---|---|---|
| FR-CG-001 | AI Configuration Management | High |
| FR-CG-002 | Search Configuration Management | Medium |
| FR-CG-003 | Feature Flag Management | High |
| FR-CG-004 | System Settings Management | Medium |

### 28. Security (SC)
| ID | Title | Priority |
|---|---|---|
| FR-SC-001 | Encryption at Rest | Critical |
| FR-SC-002 | Encryption in Transit | Critical |
| FR-SC-003 | Secrets Management | Critical |
| FR-SC-004 | Tenant Data Isolation | Critical |
| FR-SC-005 | Vulnerability Management | High |
| FR-SC-006 | Security Incident Response | Critical |

### 29. Notification (NT)
| ID | Title | Priority |
|---|---|---|
| FR-NT-001 | In-App Notifications | Medium |
| FR-NT-002 | Email Notifications | Medium |
| FR-NT-003 | Connector Failure Alerts | High |
| FR-NT-004 | Sync Completion Notifications | Low |
| FR-NT-005 | Knowledge Processing Completion Notifications | Low |

### 30. API (AP)
| ID | Title | Priority |
|---|---|---|
| FR-AP-001 | Public API Surface | High |
| FR-AP-002 | Internal Service API Surface | Critical |
| FR-AP-003 | Administrative API Surface | Medium |
| FR-AP-004 | Connector API Surface | High |
| FR-AP-005 | Webhook Support | Medium |
| FR-AP-006 | API Versioning Strategy | Critical |

## Responsibilities

- This catalog must be regenerated whenever a requirement is added, deprecated, or re-prioritized in [20_Functional_Requirements.md](20_Functional_Requirements.md); the two documents must never diverge.
- Deprecated requirements remain listed with a "Deprecated" priority marker and a reference to the superseding ADR, per [09_Governance.md](09_Governance.md) — IDs are never removed or reused.

## Constraints

- This document contains no descriptive, justification, or acceptance-criteria content. Any such content found here is out of place and should be moved to [20_Functional_Requirements.md](20_Functional_Requirements.md).

## Future Considerations

- As requirement count grows in later phases, this catalog should be supplemented with a machine-readable (e.g., CSV/JSON) export for tooling integration. Deferred to Architecture.

## Acceptance Criteria

- [ ] Every requirement in [20_Functional_Requirements.md](20_Functional_Requirements.md) appears exactly once in this catalog.
- [ ] Priority counts in the summary table sum to the total requirement count.
- [ ] No requirement appears under more than one domain.
