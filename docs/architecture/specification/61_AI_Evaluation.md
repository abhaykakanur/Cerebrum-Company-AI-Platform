# 61 — AI Evaluation

## Purpose

This document defines the Evaluation AI Subsystem Layer: the metrics by which Cerebrum's AI quality is continuously measured, and the telemetry every AI request emits to make that measurement possible. It elaborates FR-AL-003 (Knowledge Coverage Analytics, including grounding/hallucination-rate trends) from [20_Functional_Requirements.md](20_Functional_Requirements.md) and integrates with the Observability architecture in [38_Observability.md](38_Observability.md).

## Scope

This document covers evaluation metrics and AI-specific telemetry. It does not redefine the general observability architecture (structured logging, tracing, health checks — see [38_Observability.md](38_Observability.md)) beyond the AI-specific telemetry fields this layer requires.

## Definitions

- **Grounding Accuracy** — The proportion of a response's claims that are correctly supported by their cited Evidence, as determined by Evidence Verification ([58_Confidence_Engine.md](58_Confidence_Engine.md)).
- **Automated Benchmark** — A repeatable, non-human-judged evaluation run against a fixed test set, used for regression detection between releases or configuration changes.
- **Human Review** — Evaluation requiring human judgment (e.g., assessing Response Helpfulness), used where automated metrics cannot substitute for subjective quality assessment.

## Evaluation Metrics

The AI subsystem SHALL continuously measure the following twelve metrics:

| Metric | Measures | Primary Data Source |
|---|---|---|
| Grounding Accuracy | See definition above. | Validation Layer outcomes ([58_Confidence_Engine.md](58_Confidence_Engine.md)). |
| Retrieval Precision | Proportion of retrieved items that were actually relevant/used in the final response. | Retrieval Layer output vs. Citation Layer's actually-cited subset. |
| Retrieval Recall | Proportion of actually-relevant enterprise content that was successfully retrieved (requires a labeled or human-reviewed baseline for a given query). | Human Review, sampled. |
| Citation Accuracy | Proportion of citations passing Citation Verification (FR-CT-003). | Citation Layer verification outcomes. |
| Response Helpfulness | User-perceived value of the response. | User feedback (FR-CF-004) and Human Review. |
| Response Correctness | Whether the response's claims are factually accurate against enterprise knowledge. | Human Review, supplemented by Grounding Accuracy as an automated proxy. |
| Hallucination Rate | Proportion of responses containing an unsupported claim that survived to delivery (i.e., a Validation Layer miss). | Validation Layer outcomes, cross-checked by Human Review sampling. |
| Latency | Per-stage and end-to-end timing, per [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md)'s Performance Targets. | Telemetry (below). |
| Token Usage | Tokens consumed per request, by stage (prompt construction input vs. generation output). | Telemetry. |
| Cost Per Request | Derived from Token Usage and the active provider's pricing ([60_AI_Model_Abstraction.md](60_AI_Model_Abstraction.md)). | Telemetry, combined with provider cost configuration. |
| Source Coverage | The breadth of distinct Knowledge Sources (FR-CN-011 connector categories) contributing to responses over a time window — a low-diversity signal may indicate under-indexed sources. | Citation Layer source-category aggregation. |
| Confidence Calibration | Per [58_Confidence_Engine.md](58_Confidence_Engine.md)'s definition — how well stated confidence matches actual correctness (from Human Review or user feedback outcomes). | Confidence Layer scores vs. Response Correctness outcomes. |

## Evaluation Methodology

Evaluation SHALL support both automated benchmarks and human review, applied as follows:

- **Automated benchmarks** run against a maintained, versioned test-query set on a regular cadence and on every material change to Retrieval, Reasoning, or Prompt Construction architecture (per [55_Prompt_Construction.md](55_Prompt_Construction.md)'s determinism guarantee, which is what makes automated benchmark comparison meaningful) — covering Grounding Accuracy, Citation Accuracy, Hallucination Rate, Latency, and Token Usage, all of which are computable without human judgment.
- **Human review** is required for Response Helpfulness, Response Correctness (beyond what Grounding Accuracy can automatically proxy), and Retrieval Recall (which requires knowing what *should* have been retrieved, not only what was) — conducted via sampled review by domain experts, feeding both direct quality assessment and Confidence Calibration.
- Both methodologies feed the same metrics store, queryable by the Analytics Layer's existing FR-AL-003 reporting surface — this Evaluation Layer does not introduce a parallel, disconnected analytics system.

## AI Request Telemetry

Every AI request SHALL produce structured telemetry, integrating with the shared instrumentation port described in [38_Observability.md](38_Observability.md), containing the following seventeen fields:

| Field | Purpose |
|---|---|
| Request ID | Correlates telemetry with the Distributed Trace ([38_Observability.md](38_Observability.md)). |
| User ID | The requesting actor, for permission-scoped analytics and audit correlation. |
| Tenant ID | Per [46_Multi_Tenancy.md](46_Multi_Tenancy.md). |
| Workspace ID | Per the Base Entity Envelope. |
| Retriever Used | Which of the ten retrieval strategies ([52_Retrieval_Architecture.md](52_Retrieval_Architecture.md)) executed. |
| Documents Retrieved | Count and identifiers of retrieved content. |
| Graph Traversals | Count and depth of Knowledge Graph queries performed. |
| Embedding Calls | Count of embedding generation/lookup calls made during the request. |
| LLM Provider | Which provider ([60_AI_Model_Abstraction.md](60_AI_Model_Abstraction.md)) served the request. |
| Model | The specific model identifier used. |
| Latency | Per-stage breakdown, per [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md)'s Performance Targets. |
| Token Usage | Input and output token counts. |
| Estimated Cost | Derived per the Evaluation Metrics table above. |
| Confidence | The response's final Confidence Score ([58_Confidence_Engine.md](58_Confidence_Engine.md)). |
| Errors | Any error encountered, classified per [38_Observability.md](38_Observability.md)'s error taxonomy. |
| Warnings | Non-fatal degradations (e.g., a graceful fallback per [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md)'s Failure Handling). |

This telemetry SHALL integrate with the platform observability architecture — it is emitted through the same Structlog/Prometheus/OpenTelemetry instrumentation described in [38_Observability.md](38_Observability.md), not a separate, AI-specific logging pipeline, ensuring AI request behavior is visible in the same Monitoring Layer dashboards (FR-MN-004) as every other subsystem.

## Responsibilities

- Every new AI Subsystem Layer capability introduced in a later phase must emit telemetry sufficient to compute its contribution to the twelve Evaluation Metrics — a capability that cannot be measured is not considered production-ready.
- Human Review processes must be scheduled and resourced as an ongoing operational function, not a one-time launch activity, given that Response Helpfulness, Response Correctness, and Retrieval Recall have no fully automatable substitute.

## Constraints

- This document does not specify the exact benchmark test-set composition, review sampling rate, or scoring rubrics — Deferred to Architecture/operations.
- Cost Per Request depends on provider pricing data that changes over time — this document does not fix a specific cost figure.

## Future Considerations

- As the automated benchmark suite matures, it should be integrated into the CI pipeline (per [32_Technology_Stack.md](32_Technology_Stack.md)'s Pytest-based testing) so that a Prompt Construction or Retrieval change cannot regress Grounding Accuracy or Hallucination Rate without being caught before release.

## Acceptance Criteria

- [ ] All twelve evaluation metrics from the governing specification are defined with a data source.
- [ ] Both automated benchmark and human review methodologies are addressed, with a clear division of which metrics each covers.
- [ ] All seventeen telemetry fields from the governing specification are defined.
- [ ] Telemetry is explicitly integrated with, not parallel to, the platform observability architecture in [38_Observability.md](38_Observability.md).
