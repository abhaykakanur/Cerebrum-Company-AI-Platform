# 10 — Glossary

## Purpose

This document provides canonical, binding definitions for terms used throughout the Cerebrum Engineering Specification. Where a term defined here is used in any other document, this definition governs.

## Scope

This glossary covers terms introduced across the Phase 0 document set. It will grow in later phases as architecture-specific and implementation-specific terminology is introduced. Terms defined locally within a single document (and scoped to that document) are cross-referenced here but authoritatively defined in their originating document.

## Definitions

- **Architecture Decision Record (ADR)** — A documented record of a significant architectural or specification decision, including context, options considered, the decision made, and its consequences. See [09_Governance.md](09_Governance.md).
- **Architectural Review** — The governance process by which a proposed decision or change is evaluated against this specification before acceptance. See [09_Governance.md](09_Governance.md).
- **Augmentation** — Cerebrum's relationship to existing enterprise systems: reading from and adding intelligence on top of them, rather than replacing their core functionality. See [07_Non_Goals.md](07_Non_Goals.md).
- **Breaking Change** — A change to a specification, API, or schema that invalidates previously valid assumptions made by dependent work. See [09_Governance.md](09_Governance.md).
- **Cerebrum** — The Enterprise Knowledge Intelligence Platform defined by this specification.
- **Cerebrum Engineering Specification (CES)** — The versioned document set, beginning with this Phase 0 set, that authoritatively governs Cerebrum's product and engineering decisions.
- **Connector** — A component (introduced conceptually here; formally designed in later phases) responsible for collecting knowledge from a specific source system.
- **Enterprise Knowledge Intelligence Platform** — A system whose primary function is transforming fragmented organizational information into structured, searchable, explainable, trustworthy organizational intelligence. See [03_Product_Definition.md](03_Product_Definition.md).
- **Explainability** — The property that every AI-derived answer must be traceable to the data and reasoning that produced it. See [04_Project_Principles.md](04_Project_Principles.md).
- **Fragmented Knowledge** — Organizational information scattered across disconnected systems such that no single system can answer questions requiring it. See [01_Product_Vision.md](01_Product_Vision.md).
- **Grounding** — The practice of anchoring an AI-generated answer to specific, retrievable source material such that the answer can be traced back to evidence. See [01_Product_Vision.md](01_Product_Vision.md).
- **Grounding Percentage** — The proportion of AI-generated answers that are substantively supported by cited source material. See [08_Success_Metrics.md](08_Success_Metrics.md).
- **Implementation Technology** — A technology used to build Cerebrum (e.g., a vector database, a knowledge graph) that is not itself the product. See [03_Product_Definition.md](03_Product_Definition.md).
- **Institutional Knowledge** — Knowledge that exists primarily in the experience of employees rather than in a formally maintained document. See [06_Use_Cases.md](06_Use_Cases.md).
- **Knowledge Graph** — An implementation technology representing entities and their relationships; not itself the product. See [03_Product_Definition.md](03_Product_Definition.md).
- **Least Privilege** — The practice of granting the minimum access necessary for a given operation, and no more. See [04_Project_Principles.md](04_Project_Principles.md).
- **Metric Category** — A dimension of system or product health that must be measured, without a specified target value at Phase 0. See [08_Success_Metrics.md](08_Success_Metrics.md).
- **Non-Goal** — A category of functionality Cerebrum deliberately does not provide. See [07_Non_Goals.md](07_Non_Goals.md).
- **Organizational Memory** — The durable, accessible record of what an organization has decided, built, learned, and documented, independent of any individual employee's tenure. See [01_Product_Vision.md](01_Product_Vision.md).
- **Phase** — A bounded stage of Cerebrum project work with defined deliverables. See [README.md](README.md) and [00_Project_Charter.md](00_Project_Charter.md).
- **Primary Goal** — The single objective all other Cerebrum goals exist to support. See [02_Project_Goals.md](02_Project_Goals.md).
- **Principle** — A constraint on design and implementation that holds regardless of feature, phase, or team, unless formally superseded through governance. See [04_Project_Principles.md](04_Project_Principles.md).
- **Retrieval-Augmented Generation (RAG)** — An implementation technique combining retrieval of source material with generative AI reasoning; not itself the product. See [03_Product_Definition.md](03_Product_Definition.md).
- **Role** — An organizational function that implies a distinct pattern of knowledge need. See [05_Target_Users.md](05_Target_Users.md).
- **Secondary Goal** — An objective that materially advances the primary goal but is not sufficient on its own to fulfill the mission. See [02_Project_Goals.md](02_Project_Goals.md).
- **Specification** — The Cerebrum Engineering Specification (CES), version 1.0, and all documents it comprises. See [00_Project_Charter.md](00_Project_Charter.md).
- **Target User** — A role Cerebrum is explicitly designed to serve. See [05_Target_Users.md](05_Target_Users.md).
- **Use Case** — A recurring user intent that Cerebrum must be able to satisfy, independent of the specific interface used to express it. See [06_Use_Cases.md](06_Use_Cases.md).
- **Vector Database** — An implementation technology storing embeddings for similarity search; not itself the product. See [03_Product_Definition.md](03_Product_Definition.md).

## Responsibilities

- Any new term introduced in a later-phase document that is used across more than one document must be added here, with the originating document as the authoritative source.
- Where a term's meaning appears to drift between documents, this glossary's definition governs; the drifting document must be corrected.

## Constraints

- This glossary does not introduce new concepts — every entry must trace back to a definition already present in another Phase 0 document.
- Definitions here are intentionally short. Full context for a term lives in its originating document.

## Future Considerations

- As architecture and implementation phases begin, this glossary should expand to include technical terms (e.g., specific schema entities, API resource names) while preserving the product-level terms defined here unchanged.

## Acceptance Criteria

- [ ] Every term defined locally in another Phase 0 document appears here with a cross-reference.
- [ ] No entry contradicts the definition given in its originating document.
- [ ] Entries are alphabetically ordered for lookup.
