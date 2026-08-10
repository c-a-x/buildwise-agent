from __future__ import annotations

from app.core.security import hash_password
from app.models import User
from tests.conftest import login

AUDIO = b"RIFF\x00\x00\x00\x00WEBM fake audio bytes for transcription"


class FakeSpeechProvider:
    name = "fake_speech"

    def transcribe(self, audio: bytes, mime: str) -> str:
        return "请佩戴安全帽"


def _clause(*, source: str, article: str, content: str, hazard_types: list[str]) -> dict[str, object]:
    return {
        "id": "CLAUSE-001",
        "document_id": "STD-001",
        "title": "示例条款",
        "source": source,
        "article": article,
        "category": "个人防护",
        "content": content,
        "version": "",
        "effective_date": None,
        "score": 3.0,
        "metadata": {"hazard_types": hazard_types},
    }


class FakeRetrievalProvider:
    name = "fake_retrieval"

    def __init__(self, hits: list[dict[str, object]]) -> None:
        self.hits = hits

    def search(self, query: str, filters: dict[str, str], top_k: int = 3) -> list[dict[str, object]]:
        return self.hits


class FakeTextProvider:
    """离线假文本 LLM：记录 payload，返回固定答案，用于测 rag_llm 分支。"""

    name = "fake_text"
    last_payload: dict[str, object] | None = None

    def generate_worker_answer(self, payload: dict[str, object]) -> str:
        self.last_payload = payload
        return "师傅，进入现场前请检查安全帽、反光衣，并确认临边防护到位。"

    def generate_worker_message(self, payload: dict[str, object]) -> str:
        return "师傅，请按要求执行。"

    def generate_report(self, payload: dict[str, object]) -> str:
        return "日报"


def _post_transcribe(client, headers: dict[str, str], *, project_id: str = "PRJ-001", with_audio: bool = True):
    data = {"project_id": project_id}
    files = {"audio": ("voice.webm", AUDIO, "audio/webm")} if with_audio else None
    return client.post("/api/v1/worker-care/transcribe", headers=headers, data=data, files=files)


def _post_chat(client, headers: dict[str, str], *, project_id: str = "PRJ-001", question: str = "安全帽应该怎么正确佩戴？"):
    return client.post("/api/v1/worker-care/chat", headers=headers, json={"project_id": project_id, "question": question})


def test_transcribe_unconfigured_degrades(client):
    headers = login(client)

    response = _post_transcribe(client, headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["available"] is False
    assert data["reason"]
    assert data["text"] == ""
    assert data["provider"] == "off"


def test_transcribe_with_provider_returns_text(client, monkeypatch):
    import app.services.worker_care_service as worker_care_module

    monkeypatch.setattr(worker_care_module, "build_speech_provider", lambda settings: FakeSpeechProvider())
    headers = login(client)

    response = _post_transcribe(client, headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["available"] is True
    assert data["text"] == "请佩戴安全帽"
    assert data["reason"] is None
    assert data["provider"] == "fake_speech"


def test_transcribe_denied_for_outsider_project(client, db_session):
    db_session.add(User(id="USR-999", username="outsider", real_name="非项目成员", role="worker", password_hash=hash_password("BuildWise123!"), is_active=True))
    db_session.commit()

    response = _post_transcribe(client, login(client, "outsider"))

    assert response.status_code == 403


def test_transcribe_requires_audio_file(client):
    response = _post_transcribe(client, login(client), with_audio=False)
    assert response.status_code == 422


def test_chat_rag_grounds_answer_in_clause(client, monkeypatch):
    import app.services.worker_care_service as worker_care_module

    hits = [
        _clause(
            source="项目安全生产管理制度",
            article="第12条",
            content="进入施工现场的人员应正确佩戴安全帽，并扣紧下颌带。",
            hazard_types=["no_helmet"],
        )
    ]
    monkeypatch.setattr(worker_care_module, "build_retrieval_provider", lambda settings: FakeRetrievalProvider(hits))
    # LLM 未配置时走离线兜底 `_rag_answer`，避免测试打到真实 DeepSeek
    monkeypatch.setattr(worker_care_module.WorkerCareService, "_llm_ready", lambda self: False)

    response = _post_chat(client, login(client))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["answer_source"] == "rag"
    assert data["is_simulated"] is False
    assert "《项目安全生产管理制度》第12条" in data["answer"]
    assert "暂停作业" in data["answer"]  # no_helmet 属高风险
    assert len(data["citations"]) == 1
    assert data["citations"][0]["source"] == "项目安全生产管理制度"


def test_chat_rag_normal_tone_when_clause_not_high_risk(client, monkeypatch):
    import app.services.worker_care_service as worker_care_module

    hits = [_clause(source="临时规定", article="第1条", content="保持通道畅通。", hazard_types=["person_present"])]
    monkeypatch.setattr(worker_care_module, "build_retrieval_provider", lambda settings: FakeRetrievalProvider(hits))
    monkeypatch.setattr(worker_care_module.WorkerCareService, "_llm_ready", lambda self: False)

    response = _post_chat(client, login(client))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["answer_source"] == "rag"
    assert "暂停作业" not in data["answer"]
    assert "请联系安全员复查" in data["answer"]


def test_chat_rag_llm_grounds_answer_when_llm_ready(client, monkeypatch):
    import app.services.worker_care_service as worker_care_module

    hits = [
        _clause(
            source="项目安全生产管理制度",
            article="第12条",
            content="进入施工现场的人员应正确佩戴安全帽，并扣紧下颌带。",
            hazard_types=["no_helmet"],
        )
    ]
    fake_text = FakeTextProvider()
    monkeypatch.setattr(worker_care_module, "build_retrieval_provider", lambda settings: FakeRetrievalProvider(hits))
    monkeypatch.setattr(worker_care_module.WorkerCareService, "_llm_ready", lambda self: True)
    monkeypatch.setattr(worker_care_module, "build_text_provider", lambda settings: fake_text)

    response = _post_chat(client, login(client), question="进现场前要检查什么？")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["answer_source"] == "rag_llm"
    assert data["is_simulated"] is False
    assert data["answer"] == "师傅，进入现场前请检查安全帽、反光衣，并确认临边防护到位。"
    # LLM 收到的 grounding 携带问题与检索条款，而非空列表
    assert fake_text.last_payload["question"] == "进现场前要检查什么？"
    assert fake_text.last_payload["clauses"][0]["source"] == "项目安全生产管理制度"
    assert fake_text.last_payload["clauses"][0]["article"] == "第12条"


def test_chat_llm_failure_degrades_to_offline_rag(client, monkeypatch):
    import app.services.worker_care_service as worker_care_module

    hits = [_clause(source="临时规定", article="第1条", content="保持通道畅通。", hazard_types=["person_present"])]

    class _BoomTextProvider:
        name = "boom"

        def generate_worker_answer(self, payload: dict[str, object]) -> str:
            raise RuntimeError("LLM 网络故障")

    monkeypatch.setattr(worker_care_module, "build_retrieval_provider", lambda settings: FakeRetrievalProvider(hits))
    monkeypatch.setattr(worker_care_module.WorkerCareService, "_llm_ready", lambda self: True)
    monkeypatch.setattr(worker_care_module, "build_text_provider", lambda settings: _BoomTextProvider())

    response = _post_chat(client, login(client))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["answer_source"] == "rag"  # LLM 调用失败不阻断问答，降级到离线规则模板
    assert "请联系安全员复查" in data["answer"]


def test_chat_falls_back_to_template_when_no_hits(client, monkeypatch):
    import app.services.worker_care_service as worker_care_module

    monkeypatch.setattr(worker_care_module, "build_retrieval_provider", lambda settings: FakeRetrievalProvider([]))
    # LLM 未配置时走诚实提示，避免测试打到真实 DeepSeek
    monkeypatch.setattr(worker_care_module.WorkerCareService, "_llm_ready", lambda self: False)

    response = _post_chat(client, login(client))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["answer_source"] == "template"
    assert data["is_simulated"] is True
    assert data["citations"] == []
    assert "安全帽" in data["answer"]


def test_chat_no_hits_llm_general_when_llm_ready(client, monkeypatch):
    import app.services.worker_care_service as worker_care_module

    fake_text = FakeTextProvider()
    monkeypatch.setattr(worker_care_module, "build_retrieval_provider", lambda settings: FakeRetrievalProvider([]))
    monkeypatch.setattr(worker_care_module.WorkerCareService, "_llm_ready", lambda self: True)
    monkeypatch.setattr(worker_care_module, "build_text_provider", lambda settings: fake_text)

    response = _post_chat(client, login(client), question="爬塔吊要注意什么？")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["answer_source"] == "llm_general"
    assert data["is_simulated"] is True  # 非知识库条款，标为模拟
    assert data["citations"] == []
    assert data["answer"] == "师傅，进入现场前请检查安全帽、反光衣，并确认临边防护到位。"
    # LLM 收到空条款列表，明确"未检索到条款"
    assert fake_text.last_payload["question"] == "爬塔吊要注意什么？"
    assert fake_text.last_payload["clauses"] == []


def test_chat_denied_for_outsider_project(client, db_session):
    db_session.add(User(id="USR-999", username="outsider", real_name="非项目成员", role="worker", password_hash=hash_password("BuildWise123!"), is_active=True))
    db_session.commit()

    response = _post_chat(client, login(client, "outsider"))

    assert response.status_code == 403
