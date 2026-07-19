"""Configurable embedding providers — CIS Phase 3 Prompt 2's Embedding
Pipeline. :class:`HashingEmbeddingProvider` is a real, deterministic,
local implementation using the hashing trick (feature hashing) over
word tokens — the same technique scikit-learn's ``HashingVectorizer``
and Vowpal Wabbit's feature hashing are built on: texts sharing
vocabulary hash into overlapping dimensions, so cosine similarity
between their vectors genuinely reflects lexical overlap. No external
API call, no downloaded model, no LLM — this milestone's explicit
"DO NOT IMPLEMENT: LLM calls" boundary, and no network dependency this
sandbox can't guarantee (the same reasoning
cerebrum.infrastructure.extraction.ocr.NoOpOCREngine's docstring gives
for staying local). A production deployment plugs in a real hosted
embedding model (OpenAI, Cohere, a local sentence-transformer) behind
the same :class:`EmbeddingProvider` Protocol without any caller
changing — CIS Phase 3 Prompt 2's "Configurable embedding providers"
requirement.
"""

import hashlib
import math
import re
from typing import Protocol

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class EmbeddingProvider(Protocol):
    model_name: str
    dimension: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashingEmbeddingProvider:
    def __init__(self, dimension: int = 256) -> None:
        self.dimension = dimension
        self.model_name = f"hashing-trick-v1-{dimension}d"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token in _TOKEN_PATTERN.findall(text.lower()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(component * component for component in vector))
        if norm == 0.0:
            return vector
        return [component / norm for component in vector]
