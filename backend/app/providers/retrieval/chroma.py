from __future__ import annotations

from pathlib import Path

from app.knowledge.embeddings import lexical_overlap
from app.knowledge.index import KnowledgeIndex


class ChromaRetrievalProvider:
    """Persistent Chroma retrieval adapter selected by runtime settings."""

    name = "chroma"

    def __init__(self, directory: Path, min_score: float = 0.42) -> None:
        self.directory = Path(directory)
        self.min_score = max(0.0, min(1.0, min_score))
        self.index = KnowledgeIndex(self.directory)

    def search(self, query: str, filters: dict[str, str], top_k: int = 3) -> list[dict[str, object]]:
        if not query.strip() or top_k <= 0:
            return []
        candidates = self.index.query(query, top_k=max(top_k * 4, top_k))
        hazard_type = filters.get("hazard_type", "")
        results: list[dict[str, object]] = []
        for candidate in candidates:
            metadata = candidate.get("metadata")
            hazard_types = metadata.get("hazard_types", []) if isinstance(metadata, dict) else []
            if hazard_type and hazard_type not in _as_strings(hazard_types):
                continue
            distance = float(candidate.get("distance", 1.0))
            vector_score = max(0.0, min(1.0, 1.0 - distance))
            searchable_text = " ".join(
                str(candidate.get(field, ""))
                for field in ("title", "source", "article", "category", "content")
            )
            if isinstance(metadata, dict):
                searchable_text += " " + " ".join(
                    str(value)
                    for key in ("keywords", "hazard_types")
                    for value in _as_strings(metadata.get(key, []))
                )
            score = max(vector_score, lexical_overlap(query, searchable_text))
            if score < self.min_score:
                continue
            results.append(
                {
                    "id": candidate.get("id", ""),
                    "document_id": candidate.get("document_id", ""),
                    "title": candidate.get("title", ""),
                    "source": candidate.get("source", ""),
                    "article": candidate.get("article", ""),
                    "category": candidate.get("category", ""),
                    "content": candidate.get("content", ""),
                    "version": candidate.get("version", ""),
                    "effective_date": candidate.get("effective_date"),
                    "score": score,
                    "metadata": metadata if isinstance(metadata, dict) else {},
                }
            )
        results.sort(key=lambda item: float(item["score"]), reverse=True)
        return results[:top_k]


def _as_strings(value: object) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value]
    return [item for item in str(value or "").split("\u001f") if item]
