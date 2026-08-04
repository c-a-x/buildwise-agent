from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from app.knowledge.embeddings import embed_text, has_embedding_signal
from app.knowledge.types import KnowledgeClause


COLLECTION_NAME = "buildwise-standards"


class KnowledgeIndex:
    """Persistent Chroma projection for normalized source-backed clauses."""

    def __init__(self, directory: Path, collection_name: str = COLLECTION_NAME) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        try:
            import chromadb
        except ImportError as exc:  # pragma: no cover - dependency manifest covers this path
            raise RuntimeError("ChromaDB 未安装，无法使用 chroma Provider") from exc
        self.client = chromadb.PersistentClient(path=str(self.directory))
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(self, clauses: Iterable[KnowledgeClause]) -> dict[str, int]:
        records = list(clauses)
        if not records:
            return {"created": 0, "updated": 0, "deleted": 0, "count": self.count()}

        ids = [_clause_id(clause) for clause in records]
        document_ids = {clause.document_id for clause in records}
        existing = self._get_all()
        existing_metadata = {
            str(record_id)
            for record_id, metadata in zip(existing["ids"], existing["metadatas"])
            if isinstance(metadata, dict) and str(metadata.get("document_id", "")) in document_ids
        }
        existing_by_id = {
            str(record_id): (metadata, str(document))
            for record_id, metadata, document in zip(existing["ids"], existing["metadatas"], existing["documents"])
            if isinstance(metadata, dict)
        }
        incoming_metadata = {_clause_id(clause): _chroma_metadata(clause) for clause in records}
        unchanged_ids = {
            clause_id
            for clause_id, metadata in incoming_metadata.items()
            if clause_id in existing_by_id
            and existing_by_id[clause_id][0] == metadata
            and existing_by_id[clause_id][1] == next(clause.content for clause in records if _clause_id(clause) == clause_id)
        }
        stale_ids = sorted(existing_metadata - set(ids))
        if stale_ids:
            self.collection.delete(ids=stale_ids)

        self.collection.upsert(
            ids=ids,
            documents=[clause.content for clause in records],
            metadatas=[incoming_metadata[_clause_id(clause)] for clause in records],
            embeddings=[embed_text(_searchable_text(clause)) for clause in records],
        )
        created = len(set(ids) - set(existing_by_id))
        updated = len(set(ids) & set(existing_by_id) - unchanged_ids)
        return {
            "created": created,
            "updated": updated,
            "skipped": len(unchanged_ids),
            "deleted": len(stale_ids),
            "count": self.count(),
        }

    def query(self, query: str, top_k: int = 3) -> list[dict[str, object]]:
        if top_k <= 0 or not has_embedding_signal(query):
            return []
        total = self.count()
        if total == 0:
            return []
        result = self.collection.query(
            query_embeddings=[embed_text(query)],
            n_results=min(max(top_k, 1), total),
            include=["documents", "metadatas", "distances"],
        )
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        records: list[dict[str, object]] = []
        for document, metadata, distance in zip(documents, metadatas, distances):
            if not isinstance(metadata, dict):
                continue
            decoded = _decoded_metadata(metadata)
            records.append(
                {
                    "id": str(metadata.get("clause_id", "")),
                    "document_id": str(metadata.get("document_id", "")),
                    "title": str(metadata.get("title", "")),
                    "source": str(metadata.get("source", "")),
                    "article": str(metadata.get("article", "")),
                    "category": str(metadata.get("category", "")),
                    "content": str(document or ""),
                    "version": str(metadata.get("version", "")),
                    "effective_date": str(metadata.get("effective_date", "")) or None,
                    "metadata": decoded,
                    "distance": float(distance) if distance is not None else 1.0,
                }
            )
        return records

    def count(self) -> int:
        return int(self.collection.count())

    def metadata_snapshot(self) -> list[dict[str, object]]:
        result = self._get_all()
        return [_decoded_metadata(metadata) for metadata in result["metadatas"] if isinstance(metadata, dict)]

    def stats(self) -> dict[str, int]:
        snapshot = self.metadata_snapshot()
        document_ids = {str(item.get("document_id", "")) for item in snapshot if item.get("document_id")}
        return {"document_count": len(document_ids), "clause_count": len(snapshot)}

    def clear(self) -> None:
        result = self._get_all()
        ids = [str(item) for item in result["ids"]]
        if ids:
            self.collection.delete(ids=ids)

    def _get_all(self) -> dict[str, list[object]]:
        result = self.collection.get(include=["metadatas", "documents"])
        return {
            "ids": list(result.get("ids") or []),
            "metadatas": list(result.get("metadatas") or []),
            "documents": list(result.get("documents") or []),
        }


def _clause_id(clause: KnowledgeClause) -> str:
    digest = hashlib.sha256(f"{clause.article}\n{clause.content}".encode("utf-8")).hexdigest()[:20]
    return f"{clause.document_id}:{digest}"


def _searchable_text(clause: KnowledgeClause) -> str:
    return " ".join((clause.title, clause.source, clause.article, clause.category, clause.content))


def _chroma_metadata(clause: KnowledgeClause) -> dict[str, str]:
    metadata = dict(clause.metadata)
    hazard_types = _list_to_scalar(metadata.get("hazard_types"))
    keywords = _list_to_scalar(metadata.get("keywords"))
    return {
        "clause_id": _clause_id(clause),
        "document_id": clause.document_id,
        "source": clause.source,
        "title": clause.title,
        "article": clause.article,
        "category": clause.category,
        "version": clause.version,
        "effective_date": clause.effective_date or "",
        "hazard_types": hazard_types,
        "keywords": keywords,
        "metadata_json": json.dumps(metadata, ensure_ascii=False, sort_keys=True),
    }


def _decoded_metadata(metadata: dict[str, object]) -> dict[str, object]:
    raw = metadata.get("metadata_json", "{}")
    try:
        decoded = json.loads(str(raw))
    except json.JSONDecodeError:
        decoded = {}
    result = dict(decoded) if isinstance(decoded, dict) else {}
    for key in ("document_id", "source", "title", "article", "category", "version"):
        result.setdefault(key, metadata.get(key, ""))
    result.setdefault("effective_date", str(metadata.get("effective_date", "")) or None)
    for key in ("hazard_types", "keywords"):
        if key not in result:
            result[key] = _scalar_to_list(metadata.get(key, ""))
    return result


def _list_to_scalar(value: object) -> str:
    if isinstance(value, (list, tuple, set)):
        return "\u001f".join(str(item) for item in value)
    return str(value or "")


def _scalar_to_list(value: object) -> list[str]:
    text = str(value or "")
    return [item for item in text.split("\u001f") if item]
