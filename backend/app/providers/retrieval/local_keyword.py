from __future__ import annotations

import json
from pathlib import Path


BUILTIN_STANDARDS: list[dict[str, object]] = [
    {
        "id": "STD-HELMET-001",
        "category": "个人防护",
        "hazard_types": ["no_helmet"],
        "source": "项目安全生产管理制度",
        "article": "第12条",
        "content": "进入施工现场的人员应正确佩戴安全帽，并扣紧下颌带。",
        "keywords": ["安全帽", "个人防护", "施工现场"],
    },
    {
        "id": "STD-GUARDRAIL-001",
        "category": "临边防护",
        "hazard_types": ["missing_guardrail"],
        "source": "建筑施工高处作业安全技术规范",
        "article": "第4.3.1条",
        "content": "临边作业面应设置连续、稳固的防护栏杆和挡脚板。",
        "keywords": ["临边", "防护栏杆", "高处作业"],
    },
    {
        "id": "STD-VEST-001",
        "category": "个人防护",
        "hazard_types": ["no_safety_vest"],
        "source": "施工现场安全防护管理细则",
        "article": "第8条",
        "content": "进入交叉作业区域的人员应穿着符合要求的反光安全背心。",
        "keywords": ["反光背心", "安全背心", "个人防护"],
    },
]


class LocalKeywordRetrievalProvider:
    name = "local_keyword"

    def __init__(self, json_path: Path) -> None:
        self.json_path = json_path
        self._documents = self._load_documents()

    def _load_documents(self) -> list[dict[str, object]]:
        if self.json_path.exists():
            try:
                value = json.loads(self.json_path.read_text(encoding="utf-8"))
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
            except (OSError, json.JSONDecodeError):
                pass
        return BUILTIN_STANDARDS

    def stats(self) -> dict[str, int]:
        document_ids = {str(item.get("document_id", item.get("id", ""))) for item in self._documents}
        return {"document_count": len(document_ids), "clause_count": len(self._documents)}

    def search(self, query: str, filters: dict[str, str], top_k: int = 3) -> list[dict[str, object]]:
        normalized_query = query.lower()
        hazard_type = filters.get("hazard_type", "")
        scored: list[tuple[int, dict[str, object]]] = []
        for document in self._documents:
            hazard_types = [str(item) for item in document.get("hazard_types", [])]
            title = f"{document.get('category', '')} {document.get('source', '')}"
            keywords = [str(item) for item in document.get("keywords", [])]
            content = str(document.get("content", ""))
            score = 5 if hazard_type and hazard_type in hazard_types else 0
            score += sum(2 for keyword in keywords if keyword.lower() in normalized_query)
            score += sum(1 for word in normalized_query.split() if word and word in content.lower())
            if score > 0:
                scored.append((score, document))
        scored.sort(key=lambda item: item[0], reverse=True)
        results: list[dict[str, object]] = []
        for score, document in scored[:top_k]:
            hazard_types = [str(item) for item in document.get("hazard_types", [])]
            keywords = [str(item) for item in document.get("keywords", [])]
            metadata = document.get("metadata")
            normalized_metadata = dict(metadata) if isinstance(metadata, dict) else {}
            normalized_metadata.setdefault("hazard_types", hazard_types)
            normalized_metadata.setdefault("keywords", keywords)
            results.append(
                {
                    "id": str(document.get("id", "")),
                    "document_id": str(document.get("document_id", document.get("id", ""))),
                    "title": str(document.get("title", "")),
                    "source": str(document.get("source", "")),
                    "article": str(document.get("article", "")),
                    "category": str(document.get("category", "")),
                    "content": str(document.get("content", "")),
                    "version": str(document.get("version", "")),
                    "effective_date": document.get("effective_date"),
                    "score": float(score),
                    "metadata": normalized_metadata,
                }
            )
        return results
