from __future__ import annotations

import json
from pathlib import Path


BUILTIN_STANDARDS: list[dict[str, object]] = [
    {
        "id": "STD-HELMET-001",
        "category": "个人防护",
        "hazard_types": ["no_helmet"],
        "source": "JGJ 184-2009《建筑施工作业劳动防护用品配备及使用标准》",
        "article": "第2.0.4条（强制性条文）",
        "content": "进入施工现场的人员必须佩戴安全帽；作业人员应按作业要求正确使用劳动防护用品。",
        "keywords": ["安全帽", "个人防护", "施工现场"],
    },
    {
        "id": "STD-GUARDRAIL-001",
        "category": "临边防护",
        "hazard_types": ["missing_guardrail"],
        "source": "JGJ 80-2016《建筑施工高处作业安全技术规范》",
        "article": "第4.1.1条（强制性条文）",
        "content": "坠落高度基准面2m及以上进行临边作业时，应在临空一侧设置防护栏杆，并应采用密目式安全立网或工具式栏板封闭。",
        "keywords": ["临边", "防护栏杆", "高处作业"],
    },
    {
        "id": "STD-VEST-001",
        "category": "个人防护",
        "hazard_types": ["no_safety_vest"],
        "source": "GB 20653-2020《防护服装 职业用高可视性警示服》",
        "article": "第1章（范围）",
        "content": "本标准适用于可视性较低环境中，作业人员为提升自身视觉可见性而穿着的高可视性警示服（反光背心），包括建筑工地、道路施工等场所的作业人员，并应保持反光材料完好有效。",
        "keywords": ["反光背心", "高可视性警示服", "个人防护"],
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
