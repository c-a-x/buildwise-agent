from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.knowledge.index import KnowledgeIndex
from app.knowledge.types import KnowledgeClause
from app.providers.factory import build_retrieval_provider
from app.providers.retrieval.chroma import ChromaRetrievalProvider


def _clauses() -> list[KnowledgeClause]:
    return [
        KnowledgeClause(
            document_id="DOC-SAFETY-2026",
            source="已授权项目制度",
            title="施工现场安全制度",
            article="第12条",
            category="个人防护",
            content="进入施工现场的人员应正确佩戴安全帽，并扣紧下颌带。",
            version="2026.1",
            effective_date="2026-01-01",
            metadata={"hazard_types": ["no_helmet"], "keywords": ["安全帽"]},
        ),
        KnowledgeClause(
            document_id="DOC-SAFETY-2026",
            source="已授权项目制度",
            title="施工现场安全制度",
            article="第13条",
            category="临边防护",
            content="临边作业面应设置连续、稳固的防护栏杆。",
            version="2026.1",
            effective_date="2026-01-01",
            metadata={"hazard_types": ["missing_guardrail"], "keywords": ["防护栏杆"]},
        ),
    ]


def test_chroma_vector_search_preserves_metadata_and_filters(tmp_path: Path) -> None:
    index = KnowledgeIndex(tmp_path)
    index.upsert(_clauses())
    provider = ChromaRetrievalProvider(tmp_path)

    results = provider.search("安全帽", {}, top_k=3)
    assert results
    result = results[0]
    assert result["source"] == "已授权项目制度"
    assert result["article"] == "第12条"
    assert "安全帽" in str(result["content"])
    assert 0.2 <= float(result["score"]) <= 1.0
    metadata = result["metadata"]
    assert isinstance(metadata, dict)
    assert metadata["document_id"] == "DOC-SAFETY-2026"
    assert metadata["effective_date"] == "2026-01-01"
    assert metadata["hazard_types"] == ["no_helmet"]

    filtered = provider.search("安全帽", {"hazard_type": "missing_guardrail"}, top_k=3)
    assert filtered == []


def test_chroma_returns_empty_for_no_match_and_reopens_persisted_data(tmp_path: Path) -> None:
    KnowledgeIndex(tmp_path).upsert(_clauses())
    provider = ChromaRetrievalProvider(tmp_path)
    assert provider.search("完全不存在的挖掘机条款", {}, top_k=3) == []

    reopened = ChromaRetrievalProvider(tmp_path)
    results = reopened.search("安全帽", {}, top_k=1)
    assert len(results) == 1
    assert results[0]["article"] == "第12条"


def test_chroma_upsert_is_incremental_and_clear_removes_collection(tmp_path: Path) -> None:
    index = KnowledgeIndex(tmp_path)
    clauses = _clauses()
    index.upsert(clauses)
    index.upsert(clauses)
    assert index.count() == 2

    index.clear()
    assert index.count() == 0
    assert ChromaRetrievalProvider(tmp_path).search("安全帽", {}, top_k=3) == []


def test_factory_switches_to_chroma_provider(tmp_path: Path) -> None:
    provider = build_retrieval_provider(Settings(retrieval_provider="chroma", chroma_dir=tmp_path))

    assert isinstance(provider, ChromaRetrievalProvider)
