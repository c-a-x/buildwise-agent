from __future__ import annotations

import hashlib
import math
import re


EMBEDDING_DIMENSION = 384
_NGRAM_WEIGHTS = ((2, 1.0), (3, 1.6))


def embed_text(text: str) -> list[float]:
    """Create a deterministic local character n-gram embedding.

    It works for Chinese without tokenization or a model download. Chroma still
    performs the persistent vector indexing and cosine search; this embedding is
    deliberately offline and reproducible for the default deployment.
    """

    normalized = re.sub(r"\s+", "", text.lower())
    vector = [0.0] * EMBEDDING_DIMENSION
    for ngram_size, weight in _NGRAM_WEIGHTS:
        if len(normalized) < ngram_size:
            continue
        for start in range(len(normalized) - ngram_size + 1):
            ngram = normalized[start : start + ngram_size]
            digest = hashlib.blake2b(ngram.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest, "big") % EMBEDDING_DIMENSION
            vector[bucket] += weight

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def has_embedding_signal(text: str) -> bool:
    normalized = re.sub(r"\s+", "", text.lower())
    return len(normalized) >= 2


def lexical_overlap(query: str, text: str) -> float:
    """Return a bounded deterministic lexical rerank signal for vector hits."""

    normalized_query = re.sub(r"\s+", "", query.lower())
    normalized_text = re.sub(r"\s+", "", text.lower())
    if not normalized_query or not normalized_text:
        return 0.0
    if normalized_query in normalized_text:
        return 1.0
    query_grams = _ngrams(normalized_query)
    text_grams = _ngrams(normalized_text)
    if not query_grams:
        return 0.0
    return len(query_grams & text_grams) / len(query_grams)


def _ngrams(text: str) -> set[str]:
    values: set[str] = set()
    for ngram_size, _weight in _NGRAM_WEIGHTS:
        values.update(
            text[start : start + ngram_size]
            for start in range(max(0, len(text) - ngram_size + 1))
        )
    return values
