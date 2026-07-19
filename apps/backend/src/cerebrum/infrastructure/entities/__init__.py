"""CIS Phase 3 Prompt 1's Entity Extraction framework: configurable,
rule-based extractors (cerebrum.infrastructure.entities.extractors) —
regex heuristics for types with a reliable textual pattern (dates,
organization suffixes), a caller-supplied vocabulary for everything
else — deliberately not an ML/NLU model, per this milestone's explicit
"DO NOT IMPLEMENT: LLM reasoning" boundary. Consumed by
cerebrum.application.knowledge_graph.entity_service.EntityService.
"""
