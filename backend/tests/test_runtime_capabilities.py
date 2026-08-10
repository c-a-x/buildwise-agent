import sqlite3
from pathlib import Path

from app.core.config import BACKEND_DIR, Settings
from app.services.runtime_service import ProviderCapabilities, RuntimeService, _resolved_file, provider_capabilities


def capability_map(settings: Settings) -> ProviderCapabilities:
    return provider_capabilities(settings)


def test_capability_discovery_is_a_standalone_function_and_paths_are_resolved():
    assert not hasattr(RuntimeService, "provider_capabilities")
    assert _resolved_file("missing/model.pt") == (BACKEND_DIR / "missing/model.pt").resolve()


def test_default_offline_capabilities_are_explicit_and_explainable():
    # 显式指定离线文本 Provider：类默认值在 import 时从 .env 求值，无法在测试期隔离
    capabilities = capability_map(Settings(text_provider="template"))

    assert set(capabilities) == {"vision", "retrieval", "text", "speech", "weather", "tts", "broadcast"}
    assert capabilities["vision"]["provider"] == "mock"
    assert capabilities["vision"]["status"] == "simulated"
    assert capabilities["vision"]["is_simulated"] is True
    assert "离线" in str(capabilities["vision"]["reason"])
    assert capabilities["retrieval"]["provider"] == "local_keyword"
    assert capabilities["retrieval"]["status"] == "available"
    assert capabilities["retrieval"]["is_simulated"] is False
    assert "关键词" in str(capabilities["retrieval"]["reason"])
    assert capabilities["text"]["provider"] == "template"
    assert capabilities["text"]["status"] == "simulated"
    assert capabilities["text"]["is_simulated"] is True
    assert "模板" in str(capabilities["text"]["reason"])


def test_missing_yolo_dependency_or_weight_is_reported_without_loading_model(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("app.services.runtime_service._module_available", lambda name: False)
    settings = Settings(
        vision_provider="safety_hybrid",
        yolo_model_path=tmp_path / "missing-safety.pt",
    )

    capability = capability_map(settings)["vision"]

    assert capability["status"] == "simulated"
    assert capability["is_simulated"] is True
    assert "ultralytics" in str(capability["reason"])
    assert "模型" in str(capability["reason"])
    assert "安装" in str(capability["next_step"])


def test_unconfigured_ultralytics_provider_is_not_reported_as_available(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("app.services.runtime_service._module_available", lambda name: True)
    settings = Settings(
        vision_provider="ultralytics",
        vision_model_path=str(tmp_path / "missing.pt"),
    )

    capability = capability_map(settings)["vision"]

    assert capability["status"] == "unavailable"
    assert capability["is_simulated"] is False
    assert "模型" in str(capability["reason"])


def test_empty_chroma_and_optional_services_report_actionable_states(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("app.services.runtime_service._module_available", lambda name: True)
    settings = Settings(
        retrieval_provider="chroma",
        chroma_dir=tmp_path / "empty-chroma",
        text_provider="openai_compatible",
        speech_provider="openai_compatible",
        tts_provider="edge_tts",
        weather_provider="openweather",
        broadcast_webhook_url="",
        llm_base_url="",
        llm_api_key="",
        llm_model="",
        weather_api_key="",
        weather_city="",
    )

    capabilities = capability_map(settings)

    assert capabilities["retrieval"]["status"] == "not_configured"
    assert "索引" in str(capabilities["retrieval"]["reason"])
    assert capabilities["text"]["status"] == "not_configured"
    assert "LLM" in str(capabilities["text"]["reason"])
    assert capabilities["speech"]["status"] == "not_configured"
    assert "语音" in str(capabilities["speech"]["reason"])
    assert capabilities["tts"]["status"] == "configured"
    assert capabilities["weather"]["status"] == "not_configured"
    assert "天气" in str(capabilities["weather"]["reason"])
    assert capabilities["broadcast"]["status"] == "not_configured"
    assert "广播" in str(capabilities["broadcast"]["reason"])


def test_complete_unverified_real_capabilities_are_configured(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("app.services.runtime_service._module_available", lambda name: True)
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"model")
    settings = Settings(
        vision_provider="ultralytics",
        vision_model_path=str(model_path),
        text_provider="openai_compatible",
        speech_provider="openai_compatible",
        tts_provider="edge_tts",
        weather_provider="openweather",
        broadcast_webhook_url="http://broadcast.local/webhook",
        llm_base_url="http://llm.local/v1",
        llm_api_key="configured-key",
        llm_model="configured-model",
        weather_api_key="weather-key",
        weather_city="Shanghai",
    )

    capabilities = capability_map(settings)

    for key in ("vision", "text", "speech", "tts", "weather", "broadcast"):
        assert capabilities[key]["status"] == "configured"
        assert capabilities[key]["is_simulated"] is False


def test_chroma_requires_non_empty_sqlite_marker(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("app.services.runtime_service._module_available", lambda name: True)
    chroma_dir = tmp_path / "chroma"
    chroma_dir.mkdir()
    settings = Settings(retrieval_provider="chroma", chroma_dir=chroma_dir)

    unrelated_file = chroma_dir / "unrelated.txt"
    unrelated_file.write_text("not a chroma persistence marker", encoding="utf-8")
    assert capability_map(settings)["retrieval"]["status"] == "not_configured"

    marker = chroma_dir / "chroma.sqlite3"
    marker.write_bytes(b"not a sqlite database")
    assert capability_map(settings)["retrieval"]["status"] == "not_configured"
    marker.unlink()

    with sqlite3.connect(marker) as connection:
        connection.executescript(
            """
            CREATE TABLE collections (id TEXT PRIMARY KEY);
            CREATE TABLE embeddings (id TEXT PRIMARY KEY);
            """
        )
    assert marker.read_bytes()[:16] == b"SQLite format 3\x00"
    assert capability_map(settings)["retrieval"]["status"] == "available"


def test_health_exposes_capabilities_and_real_database_status(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["database"]["status"] == "connected"
    assert "capabilities" in payload
    assert payload["capabilities"]["vision"]["status"] == "simulated"
