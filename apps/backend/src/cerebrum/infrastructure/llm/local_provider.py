"""``LocalProvider``: the "Local models" ``LLMProvider`` adapter — a
real, deterministic, dependency-free extractive summarizer, never a
disguised no-op or a call to any network/ML dependency. Selects the
sentences of the prompt's retrieved context with the highest word
overlap against the question, the same "honest local approximation"
precedent
cerebrum.infrastructure.embeddings.providers.HashingEmbeddingProvider
set for embeddings (a real, inspectable algorithm — not a generative
model, and never claims to be one; every answer is prefixed to say so).

Requires no API key, no network access, and no additional dependency
(no torch/transformers) — the provider this codebase can always fall
back to, and what CIS Phase 4 Prompt 1's "RAG pipeline works end-to-end"
acceptance criterion is proven against in this sandbox, where the other
four adapters' real HTTP endpoints are unreachable (see each adapter's
own test file, which instead exercises the real HTTP request/response
handling via ``httpx.MockTransport``).
"""

import re
import uuid
from collections.abc import AsyncGenerator

from cerebrum.infrastructure.llm.provider import (
    LLMMessage,
    LLMResponse,
    LLMUsage,
)

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+|\n+")
_WORD = re.compile(r"[A-Za-z0-9]+")
_MAX_SENTENCES = 3
_DISCLAIMER = "[Local extractive summary — not a generative model response.] "
_NO_MATCH = (
    "No sentence in the retrieved context overlaps with the question's "
    "terms; here is the beginning of the retrieved context instead."
)


class LocalProvider:
    name = "local"

    def __init__(self, *, default_model: str = "local-extractive-v1") -> None:
        self.default_model = default_model

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        request_id: uuid.UUID | None = None,
    ) -> LLMResponse:
        prompt_text = "\n".join(m.content for m in messages)
        content = _DISCLAIMER + _extractive_answer(messages)
        return LLMResponse(
            content=content,
            model=model or self.default_model,
            provider=self.name,
            usage=LLMUsage(
                prompt_tokens=_estimate_tokens(prompt_text),
                completion_tokens=_estimate_tokens(content),
            ),
            finish_reason="stop",
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        request_id: uuid.UUID | None = None,
    ) -> AsyncGenerator[str, None]:
        content = _DISCLAIMER + _extractive_answer(messages)
        for word in content.split(" "):
            yield word + " "


def _extractive_answer(messages: list[LLMMessage]) -> str:
    user_messages = [m.content for m in messages if m.role == "user"]
    if not user_messages:
        return "No question was provided."
    combined = user_messages[-1]

    context_text, question = _split_context_and_question(combined)
    sentences = [s.strip() for s in _SENTENCE_BOUNDARY.split(context_text) if s.strip()]
    if not sentences:
        return "No context was retrieved for this question."

    question_terms = {w.lower() for w in _WORD.findall(question)}
    scored = [(sentence, _overlap(sentence, question_terms)) for sentence in sentences]
    matched = [s for s, score in scored if score > 0]
    if not matched:
        return _NO_MATCH + " " + " ".join(sentences[:_MAX_SENTENCES])

    ranked_order = sorted(scored, key=lambda pair: pair[1], reverse=True)
    top_sentences = {s for s, _score in ranked_order[:_MAX_SENTENCES]}
    ordered = [s for s in sentences if s in top_sentences]
    return " ".join(ordered)


def _split_context_and_question(text: str) -> tuple[str, str]:
    marker = "Question:"
    if marker in text:
        context_part, _, question_part = text.partition(marker)
        return context_part, question_part.strip()
    return text, text


def _overlap(sentence: str, question_terms: set[str]) -> int:
    sentence_terms = {w.lower() for w in _WORD.findall(sentence)}
    return len(sentence_terms & question_terms)


def _estimate_tokens(text: str) -> int:
    return max(len(text) // 4, 1)
