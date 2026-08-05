from __future__ import annotations

from app.core.security import hash_password
from app.models import User
from tests.conftest import login

AUDIO = b"RIFF\x00\x00\x00\x00WEBM fake audio bytes for transcription"


class FakeSpeechProvider:
    name = "fake_speech"

    def transcribe(self, audio: bytes, mime: str) -> str:
        return "请佩戴安全帽"


def _post_transcribe(client, headers: dict[str, str], *, project_id: str = "PRJ-001", with_audio: bool = True):
    data = {"project_id": project_id}
    files = {"audio": ("voice.webm", AUDIO, "audio/webm")} if with_audio else None
    return client.post("/api/v1/worker-care/transcribe", headers=headers, data=data, files=files)


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
