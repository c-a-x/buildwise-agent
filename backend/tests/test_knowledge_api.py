from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.knowledge.index import KnowledgeIndex
from app.knowledge.types import KnowledgeClause
from app.services import knowledge_service as knowledge_service_module
from tests.conftest import login

def test_knowledge_search_and_index_status_are_source_backed(client):
    headers = login(client)

    response = client.get("/api/v1/knowledge/search", headers=headers, params={"q": "安全帽"})

    assert response.status_code == 200
    result = response.json()["data"][0]
    assert result["document_id"]
    assert result["source"]
    assert result["article"]
    assert result["content"]
    assert isinstance(result["score"], float)
    assert isinstance(result["metadata"], dict)

    status = client.get("/api/v1/knowledge/index/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["data"]["provider"] == "local_keyword"
    assert status.json()["data"]["clause_count"] >= 1


def test_knowledge_no_hit_is_empty_and_reindex_is_available(client):
    headers = login(client)

    miss = client.get(
        "/api/v1/knowledge/search",
        headers=headers,
        params={"q": "没有授权来源的虚构条款"},
    )
    assert miss.status_code == 200
    assert miss.json()["data"] == []

    rebuilt = client.post("/api/v1/knowledge/reindex", headers=headers)
    assert rebuilt.status_code == 200
    assert rebuilt.json()["data"]["provider"] == "local_keyword"


def test_chroma_provider_is_used_by_knowledge_api(client, tmp_path: Path, monkeypatch):
    clause = KnowledgeClause(
        document_id="DOC-API-001",
        source="API 授权制度",
        title="现场防护要求",
        article="第12条",
        category="个人防护",
        content="进入现场必须佩戴安全帽。",
        version="2026",
        effective_date="2026-01-01",
        metadata={"hazard_types": ["no_helmet"]},
    )
    KnowledgeIndex(tmp_path).upsert([clause])
    monkeypatch.setattr(
        knowledge_service_module,
        "default_settings",
        Settings(retrieval_provider="chroma", chroma_dir=tmp_path),
    )
    headers = login(client)

    response = client.get("/api/v1/knowledge/search", headers=headers, params={"q": "安全帽"})
    assert response.status_code == 200
    assert response.json()["data"][0]["article"] == "第12条"

    status = client.get("/api/v1/knowledge/index/status", headers=headers)
    assert status.json()["data"]["provider"] == "chroma"
    assert status.json()["data"]["clause_count"] == 1
