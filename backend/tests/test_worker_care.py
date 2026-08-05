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

    response = _post_chat(client, login(client))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["answer_source"] == "rag"
    assert "暂停作业" not in data["answer"]
    assert "请联系安全员复查" in data["answer"]


def test_chat_falls_back_to_template_when_no_hits(client, monkeypatch):
    import app.services.worker_care_service as worker_care_module

    monkeypatch.setattr(worker_care_module, "build_retrieval_provider", lambda settings: FakeRetrievalProvider([]))

    response = _post_chat(client, login(client))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["answer_source"] == "template"
    assert data["is_simulated"] is True
    assert data["citations"] == []
    assert "安全帽" in data["answer"]


def test_chat_denied_for_outsider_project(client, db_session):
    db_session.add(User(id="USR-999", username="outsider", real_name="非项目成员", role="worker", password_hash=hash_password("BuildWise123!"), is_active=True))
    db_session.commit()

    response = _post_chat(client, login(client, "outsider"))

    assert response.status_code == 403
