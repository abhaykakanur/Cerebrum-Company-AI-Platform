"""CIS Phase 3 Prompt 3's Retrieval Engine, Context Builder &
Explainability layer — built entirely on top of CIS Phase 3 Prompt 1's
Knowledge Graph (Neo4j) and CIS Phase 3 Prompt 2's Semantic Intelligence
(Qdrant/OpenSearch/Hybrid Search) services. Query-time only: no new
pipeline stage, no new background job type (see
cerebrum.application.knowledge.knowledge_preparation_service — "Semantic
Ready" remains the pipeline's final stage). No LLM inference, prompt
generation, chat, conversation management, memory, agents, reasoning, or
tool calling — see this milestone's Non-Objectives.
"""
