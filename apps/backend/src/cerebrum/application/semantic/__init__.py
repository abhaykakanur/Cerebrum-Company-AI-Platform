"""CIS Phase 3 Prompt 2's Semantic Intelligence application services:
embedding generation (cerebrum.application.semantic.embedding_service),
vector storage/query (cerebrum.application.semantic.vector_index_service),
keyword search/indexing (cerebrum.application.semantic.search_service),
and hybrid retrieval with citations
(cerebrum.application.semantic.hybrid_search_service).

A separate application package from cerebrum.application.knowledge_graph
(Phase 3 Prompt 1's entity/relationship domain) — semantic intelligence
is built *on top of* chunks/entities, the same layering
cerebrum.application.knowledge_graph established on top of
cerebrum.application.knowledge.

No LLM calls, RAG, chat, memory, or reasoning anywhere in this package
— see this milestone's Non-Objectives.
"""
