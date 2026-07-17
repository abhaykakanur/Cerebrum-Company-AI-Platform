# 08 — Success Metrics

## Purpose

This document identifies the categories of measurement by which Cerebrum's success will be evaluated. It provides later phases with a basis for defining concrete targets, instrumentation, and dashboards.

## Scope

This document names metric categories relevant to Cerebrum's mission and principles. It does not define numeric targets, measurement methodology, or instrumentation architecture — those are planning- and architecture-phase concerns that must be defined once real system behavior exists to measure.

## Definitions

- **Metric Category** — A dimension of system or product health that must be measured, without a specified target value at this phase.
- **Grounding Percentage** — The proportion of AI-generated answers that are substantively supported by cited source material, as opposed to being produced from model knowledge alone.

## Metric Categories

1. **Search latency** — Time from query submission to results returned.
2. **Retrieval accuracy** — Correctness and relevance of retrieved knowledge relative to a query.
3. **Citation quality** — Accuracy and usefulness of the citations attached to AI-generated answers.
4. **Grounding percentage** — Proportion of answers substantively grounded in retrieved source material.
5. **Knowledge coverage** — Proportion of relevant organizational knowledge sources actually connected and indexed.
6. **Connector reliability** — Uptime and error rate of individual source-system connectors.
7. **Index freshness** — Time lag between a source-system change and its reflection in Cerebrum's index.
8. **Permission correctness** — Accuracy with which Cerebrum enforces source-system access boundaries.
9. **System uptime** — Availability of the platform as a whole.
10. **AI answer usefulness** — User-perceived value of AI-generated answers, however later measured (e.g., feedback, task completion).
11. **Developer productivity** — Impact of Cerebrum on the time engineers spend finding technical context.
12. **Documentation quality** — Improvement in the accuracy, completeness, and freshness of organizational documentation attributable to Cerebrum's use.

## Responsibilities

- Each metric category must be assigned a concrete definition, target, and measurement method before it is used to evaluate a shipped system. That work belongs to the architecture or operations phase, not Phase 0.
- Permission correctness and grounding percentage are considered trust-critical metrics: regressions in these categories should be treated with higher severity than regressions in performance-only metrics such as search latency, consistent with the Security by Default and explainability principles in [04_Project_Principles.md](04_Project_Principles.md).
- Metric ownership (which team or role is accountable for each category) is out of scope for this document and should be assigned during planning.

## Constraints

- No numeric targets, SLAs, or thresholds are defined in this document. Any number appearing in later communications about these metrics must trace back to a documented decision, not to this specification.
- Metric categories here are not a complete monitoring specification; they identify what must eventually be measured, not how.

## Future Considerations

- As real usage data becomes available, target values and acceptable ranges should be defined per category and recorded in a dedicated metrics or SLA document.
- Additional metric categories may emerge from new use cases (e.g., a metric for expert-location accuracy) and should be added here through governance review so the full metric set stays traceable to goals in [02_Project_Goals.md](02_Project_Goals.md).

## Acceptance Criteria

- [ ] All twelve metric categories from the governing specification are listed.
- [ ] No numeric target, threshold, or SLA is stated in this document.
- [ ] Trust-critical metrics (permission correctness, grounding percentage) are flagged as such.
