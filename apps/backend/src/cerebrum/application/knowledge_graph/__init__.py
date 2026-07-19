"""CIS Phase 3 Prompt 1's Knowledge Graph & Entity Intelligence
application services: entity/relationship CRUD and dedup
(cerebrum.application.knowledge_graph.entity_service,
cerebrum.application.knowledge_graph.relationship_service), canonical
entity resolution (cerebrum.application.knowledge_graph.deduplication),
and pipeline orchestration
(cerebrum.application.knowledge_graph.knowledge_graph_service) — the
Chunk -> Entity Extraction -> Relationship Extraction -> Graph Update
stage CIS Phase 2 Prompt 4's
cerebrum.application.knowledge.knowledge_preparation_service.KnowledgePreparationService
now calls after Chunking succeeds.

A separate application package from cerebrum.application.knowledge
(Phase 2's Document/Chunk domain) rather than folded into it — entities
and relationships are a distinct bounded context built *on top of*
chunks, the same separation cerebrum.application.auth already
established from cerebrum.application.knowledge.

No embeddings, vector search, hybrid search, ranking, RAG, chat, or LLM
reasoning anywhere in this package — see this milestone's Non-Objectives.
"""
