"""CIS Phase 4 Prompt 1's Enterprise RAG Engine & AI Orchestration —
built entirely on top of CIS Phase 3's Retrieval Engine (Prompt 3),
Semantic Intelligence (Prompt 2), and Knowledge Graph (Prompt 1)
services: this layer never queries Qdrant/OpenSearch/Neo4j/PostgreSQL
directly, only
:class:`~cerebrum.application.retrieval.retrieval_service.RetrievalService`,
:class:`~cerebrum.application.retrieval.context_builder_service.ContextBuilderService`,
and
:class:`~cerebrum.application.retrieval.citation_service.CitationService`
— see cerebrum.application.retrieval's package docstring for the same
"consume, don't bypass" principle this milestone's OBJECTIVE restates
one layer up.

No conversation memory, multi-agent workflows, task execution, tool
calling, or automation — see this milestone's Non-Objectives. Every
call is a single question against a single workspace's already-indexed
knowledge, answered once.
"""
