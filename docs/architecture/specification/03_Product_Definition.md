# 03 — Product Definition

## Purpose

This document states precisely what Cerebrum is, what it is not, and the core responsibilities it must fulfill. It exists to prevent the product from being informally redefined as "a chatbot," "a search tool," or any other reduction of its actual scope during later implementation phases.

## Scope

This document covers product-category definition and core functional responsibilities. Target users and use cases are covered separately in [05_Target_Users.md](05_Target_Users.md) and [06_Use_Cases.md](06_Use_Cases.md). Explicit exclusions relative to adjacent enterprise software categories are covered in [07_Non_Goals.md](07_Non_Goals.md).

## Definitions

- **Enterprise Knowledge Intelligence Platform** — A system whose primary function is transforming fragmented organizational information into structured, searchable, explainable, trustworthy organizational intelligence.
- **Implementation Technology** — A technology used to build Cerebrum (e.g., a vector database, a knowledge graph) that is not itself the product.

## Product Category

Cerebrum is an **Enterprise Knowledge Intelligence Platform**. Its responsibility is to transform fragmented organizational information into structured, searchable, explainable, trustworthy organizational intelligence.

## What Cerebrum Is Not

The following are implementation technologies that Cerebrum may use internally. None of them individually describe the product:

- Cerebrum is **not merely** an AI chatbot.
- Cerebrum is **not** a document search engine.
- Cerebrum is **not** a vector database.
- Cerebrum is **not** a knowledge graph.
- Cerebrum is **not simply** a retrieval-augmented generation (RAG) application.

These are components that later architecture phases may select and combine. The product is the enterprise intelligence layer built on top of them — the responsibilities below, delivered together, as a coherent system.

## Core Responsibilities

Cerebrum shall perform the following functions. Each is a required capability of the platform, not an optional feature:

1. **Collect** knowledge from source systems across the organization.
2. **Normalize** knowledge into consistent, processable representations regardless of source format.
3. **Understand** knowledge through semantic interpretation of content.
4. **Extract** structured facts, entities, and relationships from unstructured and semi-structured content.
5. **Structure** knowledge so it can be reliably retrieved and reasoned over.
6. **Relate** knowledge across sources, surfacing connections not visible within any single source system.
7. **Store** knowledge durably.
8. **Version** knowledge so that history is preserved rather than overwritten.
9. **Search** knowledge with relevance and speed appropriate to enterprise use.
10. **Reason** over knowledge to answer questions requiring synthesis across multiple sources.
11. **Explain** knowledge-derived answers, including their sources and confidence.
12. **Preserve** knowledge against loss, including loss caused by organizational or personnel change.
13. **Visualize** knowledge and the relationships between its parts.
14. **Protect** knowledge through permission-aware access control at every layer.
15. **Continuously improve** knowledge quality through feedback and correction over time.

## Responsibilities of This Document

- This definition is binding on all future architecture and implementation phases.
- Any future phase that proposes to drop one of the fifteen core responsibilities, or to describe Cerebrum solely in terms of one implementation technology, must raise an ADR per [09_Governance.md](09_Governance.md) rather than proceeding silently.

## Constraints

- This document does not prescribe *how* any responsibility is implemented (e.g., which vector database, which graph model). That is the responsibility of later architecture phases.
- The "what Cerebrum is not" list is not exhaustive of every technology Cerebrum might use — it is illustrative of the category error to avoid (reducing the product to a single component).

## Future Considerations

- As new categories of enterprise systems emerge (e.g., new communication platforms), the collection responsibility's scope should be revisited without altering the fifteen core responsibilities themselves.
- The relationship between "core responsibilities" here and future service/module boundaries in the technical architecture should be made explicit once architecture phases begin — this document intentionally stays implementation-agnostic.

## Acceptance Criteria

- [ ] The product category is stated as a single unambiguous sentence.
- [ ] All five "is not" clarifications are present and consistent with the governing specification.
- [ ] All fifteen core responsibilities from the governing specification are present, unaltered in substance.
- [ ] The document does not introduce any implementation detail (specific database, framework, or vendor).
