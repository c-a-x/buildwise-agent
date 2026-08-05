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


def test_knowledge_chat_rag_only_returns_sections_and_citations(client):
    response = client.post("/api/v1/knowledge/chat", headers=login(client), json={"question": "进入施工现场对安全帽有什么要求？"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["mode"] == "rag_only"
    assert data["description"] == "离线检索拼装"
    assert "【一、规范与标准条文】" in data["answer"]
    assert "安全帽" in data["answer"]
    assert data["citations"]
    assert data["citations"][0]["type"] == "clause"
    assert data["retrieval"]["clauses"]["ready"] is True
    assert data["llm"]["used"] is False


def test_knowledge_chat_risk_keyword_hits_risk_tip(client):
    response = client.post("/api/v1/knowledge/chat", headers=login(client), json={"question": "临边防护怎么做才合规？"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["retrieval"]["risk_tip"]["included"] is True
    assert "missing_guardrail" in data["retrieval"]["risk_tip"]["hazard_types"]
    assert "命中风险类型「临边防护缺失」" in data["answer"]
    assert "project_manager" in data["answer"]  # 责任人取自 risk_rules


def test_knowledge_chat_appends_site_summary_when_project_given(client, db_session):
    from datetime import datetime, timezone

    from app.models import AgentRun, Incident, Upload

    created_at = datetime.now(timezone.utc)
    db_session.add(Upload(id="UPL-CHAT-001", project_id="PRJ-001", uploaded_by="USR-002", original_name="a.jpg", stored_name="a.jpg", mime_type="image/jpeg", size_bytes=4, relative_path="uploads/a.jpg", sha256="0" * 64, created_at=created_at))
    db_session.add(AgentRun(id="TASK-CHAT-001", project_id="PRJ-001", upload_id="UPL-CHAT-001", requested_by="USR-002", location="B1", work_type="主体结构", status="completed", is_simulated=True, created_at=created_at, finished_at=created_at))
    db_session.add(Incident(id="INC-CHAT-001", agent_run_id="TASK-CHAT-001", project_id="PRJ-001", upload_id="UPL-CHAT-001", hazard_type="no_helmet", hazard_name="未佩戴安全帽", description="现场概况测试", confidence=0.9, risk_level="high", metadata_json={"module": "quality"}, created_at=created_at))
    db_session.commit()

    response = client.post("/api/v1/knowledge/chat", headers=login(client), json={"question": "安全帽", "project_id": "PRJ-001"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["retrieval"]["site"]["included"] is True
    assert "【三、现场概况】" in data["answer"]
    assert "近 7 天" in data["answer"]
    assert "质量 1 条" in data["answer"]
    assert "未闭环整改工单" in data["answer"]


def test_knowledge_chat_requires_question(client):
    response = client.post("/api/v1/knowledge/chat", headers=login(client), json={"question": ""})
    assert response.status_code == 422


def test_knowledge_chat_denied_for_outsider_project(client, db_session):
    from app.core.security import hash_password
    from app.models import User

    db_session.add(User(id="USR-999", username="outsider", real_name="非项目成员", role="safety_officer", password_hash=hash_password("BuildWise123!"), is_active=True))
    db_session.commit()

    response = client.post("/api/v1/knowledge/chat", headers=login(client, "outsider"), json={"question": "安全帽", "project_id": "PRJ-001"})
    assert response.status_code == 403
