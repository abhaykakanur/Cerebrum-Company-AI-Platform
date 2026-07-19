"""Proves CIS Phase 3 Prompt 2's ``HashingEmbeddingProvider``: correct
dimensionality, unit-norm vectors, determinism, and — the property that
actually matters for retrieval — that texts sharing vocabulary produce
measurably more similar vectors than unrelated texts.
"""

import math

import pytest

from cerebrum.infrastructure.embeddings.providers import HashingEmbeddingProvider

pytestmark = pytest.mark.unit


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def test_vectors_have_the_configured_dimension() -> None:
    provider = HashingEmbeddingProvider(dimension=128)
    vectors = provider.embed(["hello world", "goodbye world"])
    assert all(len(v) == 128 for v in vectors)


def test_vectors_are_unit_normalized() -> None:
    provider = HashingEmbeddingProvider(dimension=64)
    (vector,) = provider.embed(["the quick brown fox jumps over the lazy dog"])
    norm = math.sqrt(sum(component * component for component in vector))
    assert norm == pytest.approx(1.0)


def test_embedding_is_deterministic() -> None:
    provider = HashingEmbeddingProvider(dimension=64)
    assert provider.embed(["hello world"]) == provider.embed(["hello world"])


def test_empty_text_produces_a_zero_vector_without_error() -> None:
    provider = HashingEmbeddingProvider(dimension=32)
    (vector,) = provider.embed([""])
    assert vector == [0.0] * 32


def test_similar_texts_are_closer_than_unrelated_texts() -> None:
    provider = HashingEmbeddingProvider(dimension=256)
    vectors = provider.embed(
        [
            "The quick brown fox jumps over the lazy dog",
            "A fast brown fox leaps over a sleepy dog",
            "Quantum computing uses qubits for parallel computation",
        ]
    )
    similar_pair_similarity = _cosine(vectors[0], vectors[1])
    unrelated_pair_similarity = _cosine(vectors[0], vectors[2])
    assert similar_pair_similarity > unrelated_pair_similarity


def test_model_name_reflects_the_configured_dimension() -> None:
    provider = HashingEmbeddingProvider(dimension=128)
    assert "128" in provider.model_name
