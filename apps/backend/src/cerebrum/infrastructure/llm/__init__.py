"""LLM provider adapters — CIS Phase 4 Prompt 1's LLM Abstraction.
``LLMProvider`` (see ``provider.py``) is the one interface
cerebrum.application.ai depends on; every concrete adapter here
(``OpenAIProvider``, ``AnthropicProvider``, ``GeminiProvider``,
``OllamaProvider``, ``LocalProvider``) implements it against a
different backend, so no application-layer code ever branches on which
provider is active — see
docs/architecture/specification/60_AI_Model_Abstraction.md's Provider
Independence Principle.
"""
