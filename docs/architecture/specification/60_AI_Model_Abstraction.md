# 60 — AI Model Abstraction

## Purpose

This document defines the AI Model Abstraction architecture: how Cerebrum avoids dependency on any single model provider, which providers are supported, and how embedding generation is architected. It elaborates the `LLMProviderPort` and `EmbeddingProviderPort` interfaces first introduced in [31_Component_Architecture.md](31_Component_Architecture.md) and [34_Architecture_Principles.md](34_Architecture_Principles.md), and the provider-evaluation decisions in [32_Technology_Stack.md](32_Technology_Stack.md).

## Scope

This document covers provider abstraction and embedding architecture. It does not cover retrieval mechanics that consume embeddings (see [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md)) or AI Administration's provider-credential configuration surface (see [62_AI_Governance.md](62_AI_Governance.md), which this document's abstraction makes possible).

## Definitions

- **Provider** — An external or self-hosted service supplying LLM inference or embedding generation.
- **Provider Abstraction** — The architectural guarantee that Cerebrum's domain and application code never references a specific provider's SDK or API shape directly.

## Provider Independence Principle

Cerebrum SHALL never depend directly on one model provider. This directly restates and reinforces the decision already made in [32_Technology_Stack.md](32_Technology_Stack.md): Cerebrum builds its own orchestration layer against `LLMProviderPort` and `EmbeddingProviderPort` interfaces (per Dependency Inversion, [34_Architecture_Principles.md](34_Architecture_Principles.md)), precisely so that provider independence is structural, not aspirational. This document elaborates that decision with the specific provider list and switching mechanics the Part 5 specification requires.

**Business logic SHALL remain provider-independent.** No AI Subsystem Layer described in documents 50–59 — Query Understanding, Query Planning, Retrieval, Context Construction, Reasoning, Response Generation, Citation, Confidence, Validation, or Memory — SHALL contain a conditional branch keyed on which provider is active. Provider-specific behavior (message formatting, token counting idiosyncrasies, rate-limit handling) is confined entirely to the Infrastructure Layer adapter implementing the relevant port, per [33_Directory_Structure.md](33_Directory_Structure.md)'s `backend/ai/reasoning/infrastructure/` location.

## Supported Providers

The architecture SHALL support the following provider categories via `LLMProviderPort` adapters:

| Provider | Notes |
|---|---|
| OpenAI | |
| Anthropic | |
| Google Gemini | |
| Azure OpenAI | A distinct adapter from OpenAI despite API similarity, since authentication, deployment model, and data-residency characteristics differ materially for enterprise procurement reasons. |
| OpenRouter | A multi-provider routing service; supported as its own adapter (not a substitute for direct provider adapters) since it offers a distinct value proposition (provider fallback, cost arbitrage) that some deployments may prefer over Cerebrum's own fallback logic. |
| Local Models | Self-hosted inference (e.g., via an OpenAI-API-compatible local server), supporting deployments with data-residency or air-gapped requirements that preclude any external API call. |
| Future Providers | The port interface is designed such that a new provider requires only a new adapter, per the Plugin-Readiness pattern established for the AI Layer in [31_Component_Architecture.md](31_Component_Architecture.md) — no core reasoning logic changes. |

**Provider switching SHALL require configuration changes only** — selecting a different default or fallback provider (per [62_AI_Governance.md](62_AI_Governance.md)'s AI Administration settings) is a configuration change, never a code change or redeployment of AI Subsystem Layer logic.

## Provider Selection and Fallback

An organization's or workspace's active provider selection (default model, fallback model, per [62_AI_Governance.md](62_AI_Governance.md)) is resolved at LLM Invocation time (stage 12, [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md)). Where the default provider fails (Provider Timeout, Provider Failure per [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md)'s Failure Handling), the configured fallback model is attempted before the request fails visibly — this directly informs the resolution of Open Question 42 in [40_Open_Questions.md](40_Open_Questions.md) (LLM/embedding provider fallback policy): the fallback policy is **organization-configurable fallback-to-a-second-configured-model**, with the specific default fallback chain Deferred to Architecture.

## Embedding Strategy

Embedding generation SHALL support the following content types, each entering the embedding pipeline via Knowledge Processing's `Embed` stage ([45_Data_Lifecycle.md](45_Data_Lifecycle.md)):

| Content Type | Notes |
|---|---|
| Documents | Whole-document embeddings, where a document-level (not only chunk-level) representation benefits retrieval (e.g., document-level semantic clustering). |
| Chunks | The primary embedding unit, per FR-KP-009. |
| Meeting Transcripts | Embedded per-Chunk after Meeting Intelligence processing ([45_Data_Lifecycle.md](45_Data_Lifecycle.md)). |
| Policies | Embedded as a specialized Document, inheriting standard Chunk embedding. |
| Architecture Documents | Embedded as a specialized Document; may warrant a code-aware or diagram-aware embedding model variant (Deferred to Architecture). |
| Code Snippets | Embedded using a code-aware embedding model where available, distinct from natural-language embedding, given code's different semantic structure. |
| Knowledge Graph Metadata | Entity/relationship descriptions may be embedded to support semantic entity search, complementing Neo4j's structural traversal with Qdrant's semantic similarity for entity discovery. |

### Embedding Metadata

Every Embedding, per [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md)'s entity definition, SHALL carry:

| Field | Purpose |
|---|---|
| Embedding Version | Supports the re-embedding cutover mechanics referenced in Open Question 23 of [27_Open_Questions.md](27_Open_Questions.md). |
| Embedding Model | The specific model identifier used to generate this vector. |
| Creation Timestamp | Per the Base Entity Envelope ([44_Global_Entity_Model.md](44_Global_Entity_Model.md)). |
| Chunk Reference | The source Chunk this embedding represents (or Document/Meeting/other content-type reference, per the table above). |
| Tenant ID | Per [46_Multi_Tenancy.md](46_Multi_Tenancy.md)'s Qdrant isolation requirement. |
| Workspace ID | Per the Base Entity Envelope. |
| Language | Supporting multilingual retrieval quality assessment (FR-KI-008). |
| Vector Dimension | Recorded explicitly since different embedding models produce different-dimension vectors, relevant to the regeneration process below. |

### Embedding Regeneration

Embeddings SHALL support regeneration whenever embedding models change. This directly implements the cutover mechanics Open Question 23 in [27_Open_Questions.md](27_Open_Questions.md) flagged as architecture-time-deferred: a model change triggers a Background Processing Task ([36_Background_Processing.md](36_Background_Processing.md)) that regenerates embeddings for affected content, with the old and new Embedding Versions coexisting (per [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md)'s "Versioned: Yes" designation) until the new version's regeneration is confirmed complete, at which point the old version is superseded — never a hard cutover that risks a search-availability gap.

## Responsibilities

- Every new provider adapter added in a later phase must implement the existing `LLMProviderPort`/`EmbeddingProviderPort` interface without requiring changes to any AI Subsystem Layer's domain or application code — a proposed provider integration requiring such a change is a design defect, not an acceptable exception.
- Embedding Regeneration must be triggered for every embedding model change, including provider switches that use a different underlying embedding model — a partial regeneration leaving mixed-model-version embeddings queryable together without accounting for their different vector spaces is a correctness defect.

## Constraints

- This document does not commit to a default provider — Deferred to Architecture, per Open Question 10 in [11_Open_Questions.md](11_Open_Questions.md) and Open Question 42 in [40_Open_Questions.md](40_Open_Questions.md).
- This document does not specify exact embedding dimensions, model names/versions, or vector distance metrics — Deferred to Architecture.

## Future Considerations

- As new embedding-worthy content types emerge (e.g., a dedicated diagram/image embedding model for architecture diagrams), they should be added to the Embedding Strategy table following the same content-type pattern.

## Acceptance Criteria

- [ ] The Provider Independence principle is stated as structurally enforced (via ports), not merely a stated preference.
- [ ] All seven supported provider categories from the governing specification are listed.
- [ ] Provider switching is stated as a configuration-only change.
- [ ] All seven content types and eight embedding metadata fields from the governing specification are addressed, along with the regeneration requirement.
- [ ] Open Question 42 from [40_Open_Questions.md](40_Open_Questions.md) is explicitly informed/partially resolved by this document's fallback policy statement.
