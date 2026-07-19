"""CIS Phase 4 Prompt 2's Conversational AI, Memory & Intelligent
Sessions — persistent conversations built on top of CIS Phase 4 Prompt
1's Enterprise RAG Engine
(:class:`~cerebrum.application.ai.rag_service.RAGService`), never
duplicating retrieval, prompting, or generation logic: this layer adds
persistence
(:class:`~cerebrum.infrastructure.database.models.conversation.Conversation`/
:class:`~cerebrum.infrastructure.database.models.message.Message`),
rolling-window/summarized memory, and session lifecycle around calls
``RAGService`` already knows how to make.

No multi-agent systems, workflow automation, task execution, enterprise
connectors, or Employee Knowledge Capsule — see this milestone's
Non-Objectives.
"""
