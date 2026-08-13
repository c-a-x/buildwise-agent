"""语音广播（/broadcast-test 与 broadcast_service）测试。"""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest

from app.core.config import settings
from app.core.exceptions import AppError
from app.providers.vision.yolo import YOLODetector
from app.services.broadcast_service import (
    broadcast_voice_alert,
    build_broadcast_message,
    send_test_broadcast,
)
from tests.conftest import login


def _hazard(name: str, risk_level: str = "high", hazard_type: str = "no_helmet") -> dict[str, Any]:
    return {
        "hazard_type": hazard_type,
        "hazard_name": name,
        "description": "检测到违规。",
        "confidence": 0.9,
        "risk_level": risk_level,
        "bbox": [0.1, 0.1, 0.4, 0.6],
        "source": "yolo",
    }


def _jpeg_bytes() -> bytes:
    return b"\xff\xd8\xff\xe0" + b"\x00" * 64


class TestBuildBroadcastMessage:
    def test_joins_unique_names(self):
        hazards = [
            _hazard("未佩戴安全帽"),
            _hazard("未佩戴安全帽"),  # 去重
            _hazard(" 未穿反光安全背心 "),  # 去首尾空格
            _hazard("未佩戴口罩", hazard_type="no_mask"),
            {"hazard_name": ""},  # 空串忽略
        ]
        assert build_broadcast_message(hazards) == "警告！检测到未佩戴安全帽、未穿反光安全背心、未佩戴口罩，请立即整改。"

    def test_caps_at_three_names(self):
        many = [_hazard(f"隐患{i}") for i in range(5)]
        message = build_broadcast_message(many)
        assert "隐患3" not in message
        assert message.count("、") == 2

    def test_empty_or_blank_names(self):
        assert build_broadcast_message([]) == ""
        assert build_broadcast_message([{"hazard_name": "  "}]) == ""


class TestBroadcastVoiceAlert:
    def test_noop_without_webhook(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.broadcast_service._dispatch",
            lambda *a, **k: pytest.fail("未配置 webhook 时不应发起推送"),
        )
        broadcast_voice_alert([_hazard("未佩戴安全帽")], settings)  # 默认 BROADCAST_WEBHOOK_URL 为空
        assert True

    def test_posts_text_and_audio_with_mock_tts(self, monkeypatch):
        captured: dict[str, Any] = {}

        def fake_dispatch(payload: dict[str, Any], webhook_url: str) -> bool:
            captured["payload"] = payload
            captured["url"] = webhook_url
            return True

        monkeypatch.setattr("app.services.broadcast_service._dispatch", fake_dispatch)
        fake_settings = dataclasses.replace(
            settings, broadcast_webhook_url="http://speaker/api/tts", tts_provider="mock"
        )
        broadcast_voice_alert([_hazard("未佩戴安全帽"), _hazard("未穿反光安全背心")], fake_settings)

        payload = captured["payload"]
        assert captured["url"] == "http://speaker/api/tts"
        assert payload["message"] == "警告！检测到未佩戴安全帽、未穿反光安全背心，请立即整改。"
        assert payload["audio_base64"]
        assert payload["audio_format"] == "mp3"
        assert payload["tts"] == {"provider": "mock", "available": True, "is_simulated": True}

    def test_degrades_to_text_only_when_synthesis_fails(self, monkeypatch):
        captured: dict[str, Any] = {}

        def fake_dispatch(payload: dict[str, Any], webhook_url: str) -> bool:
            captured["payload"] = payload
            return True

        monkeypatch.setattr("app.services.broadcast_service._dispatch", fake_dispatch)

        class FailingProvider:
            name = "edge_tts"
            is_simulated = False

            def synthesize(self, text: str) -> bytes:
                raise AppError("TTS 合成失败", "TTS_SYNTHESIS_FAILED", 500)

        monkeypatch.setattr(
            "app.services.broadcast_service.build_tts_provider",
            lambda cfg: FailingProvider(),
        )
        fake_settings = dataclasses.replace(
            settings, broadcast_webhook_url="http://speaker/api/tts", tts_provider="edge_tts"
        )
        broadcast_voice_alert([_hazard("未佩戴安全帽")], fake_settings)

        payload = captured["payload"]
        assert payload["message"]
        assert "audio_base64" not in payload
        assert payload["tts"] == {"provider": None, "available": False, "is_simulated": False}


class TestSendTestBroadcast:
    def test_returns_delivered_with_mock_tts(self, monkeypatch):
        monkeypatch.setattr("app.services.broadcast_service._dispatch", lambda *a, **k: True)
        fake_settings = dataclasses.replace(
            settings, broadcast_webhook_url="http://speaker/api/tts", tts_provider="mock"
        )
        result = send_test_broadcast(fake_settings)
        assert result["delivered"] is True
        assert result["reason"] is None
        assert result["message"].startswith("警告！")
        assert result["tts"]["provider"] == "mock"
        assert result["tts"]["available"] is True

    def test_reports_not_configured(self, monkeypatch):
        monkeypatch.setattr("app.services.broadcast_service._dispatch", lambda *a, **k: True)
        fake_settings = dataclasses.replace(settings, broadcast_webhook_url="")
        result = send_test_broadcast(fake_settings)
        assert result["delivered"] is False
        assert result["reason"] == "未配置 BROADCAST_WEBHOOK_URL"


class TestDetectFrameIntegration:
    def test_triggers_broadcast_on_high(self, client, monkeypatch):
        fake_hazards = [_hazard("未佩戴安全帽")]
        monkeypatch.setattr("app.providers.vision.yolo.load_model", lambda path: object())
        monkeypatch.setattr(YOLODetector, "detect", lambda self, image_path: fake_hazards)
        called: list[tuple[list, object]] = []
        monkeypatch.setattr(
            "app.api.v1.endpoints.safety.broadcast_voice_alert",
            lambda hazards, cfg: called.append((hazards, cfg)),
        )
        fake_settings = dataclasses.replace(
            settings, broadcast_webhook_url="http://127.0.0.1:9", tts_provider="off"
        )
        monkeypatch.setattr("app.api.v1.endpoints.safety.settings", fake_settings)

        headers = login(client)
        response = client.post(
            "/api/v1/safety/detect-frame",
            files={"image": ("f.jpg", _jpeg_bytes(), "image/jpeg")},
            headers=headers,
        )
        assert response.status_code == 200
        assert len(called) == 1
        assert called[0][0] == fake_hazards

    def test_skips_broadcast_when_not_configured(self, client, monkeypatch):
        fake_hazards = [_hazard("未佩戴安全帽")]
        monkeypatch.setattr("app.providers.vision.yolo.load_model", lambda path: object())
        monkeypatch.setattr(YOLODetector, "detect", lambda self, image_path: fake_hazards)
        called: list[tuple[list, object]] = []
        monkeypatch.setattr(
            "app.api.v1.endpoints.safety.broadcast_voice_alert",
            lambda hazards, cfg: called.append((hazards, cfg)),
        )
        fake_settings = dataclasses.replace(settings, broadcast_webhook_url="", tts_provider="off")
        monkeypatch.setattr("app.api.v1.endpoints.safety.settings", fake_settings)

        headers = login(client)
        response = client.post(
            "/api/v1/safety/detect-frame",
            files={"image": ("f.jpg", _jpeg_bytes(), "image/jpeg")},
            headers=headers,
        )
        assert response.status_code == 200
        assert called == []

    def test_broadcast_test_endpoint_requires_auth(self, client):
        response = client.post("/api/v1/safety/broadcast-test")
        assert response.status_code == 401


class TestBroadcastDeduplication:
    """broadcast_voice_alert 去重：同一批隐患不随 1 帧/秒轮询重复轰炸音响。"""

    def _settings(self) -> Any:
        return dataclasses.replace(settings, broadcast_webhook_url="http://speaker/api/tts", tts_provider="off")

    def test_same_hazards_suppressed_within_cooldown(self, monkeypatch):
        dispatched: list[dict[str, Any]] = []
        monkeypatch.setattr(
            "app.services.broadcast_service._dispatch",
            lambda payload, url: dispatched.append(payload) or True,
        )
        monkeypatch.setattr("app.services.broadcast_service._LAST_KEY", "")
        monkeypatch.setattr("app.services.broadcast_service._LAST_AT", 0.0)
        s = self._settings()
        broadcast_voice_alert([_hazard("未佩戴安全帽")], s)
        broadcast_voice_alert([_hazard("未佩戴安全帽")], s)  # 同签名：冷却窗口内不重复
        broadcast_voice_alert([_hazard("未佩戴安全帽"), _hazard("未佩戴口罩", hazard_type="no_mask")], s)
        assert len(dispatched) == 2  # 第 1 次 + 隐患集合变化的第 3 次

    def test_reaannounce_same_hazards_after_cooldown(self, monkeypatch):
        dispatched: list[dict[str, Any]] = []
        monkeypatch.setattr(
            "app.services.broadcast_service._dispatch",
            lambda payload, url: dispatched.append(payload) or True,
        )
        monkeypatch.setattr("app.services.broadcast_service._LAST_KEY", "")
        monkeypatch.setattr("app.services.broadcast_service._LAST_AT", 0.0)
        s = self._settings()
        broadcast_voice_alert([_hazard("未佩戴安全帽")], s)
        # 模拟冷却时间已过（回到 0），同一批隐患应重新播报
        monkeypatch.setattr("app.services.broadcast_service._LAST_AT", 0.0)
        broadcast_voice_alert([_hazard("未佩戴安全帽")], s)
        assert len(dispatched) == 2

    def test_failed_dispatch_not_remembered(self, monkeypatch):
        import app.services.broadcast_service as bsvc

        dispatched: list[dict[str, Any]] = []
        monkeypatch.setattr(
            "app.services.broadcast_service._dispatch",
            lambda payload, url: dispatched.append(payload) or False,  # 总是失败
        )
        monkeypatch.setattr("app.services.broadcast_service._LAST_KEY", "")
        monkeypatch.setattr("app.services.broadcast_service._LAST_AT", 0.0)
        s = self._settings()
        broadcast_voice_alert([_hazard("未佩戴安全帽")], s)
        broadcast_voice_alert([_hazard("未佩戴安全帽")], s)  # 失败未记忆 → 同签名仍应重试
        assert len(dispatched) == 2
        assert bsvc._LAST_KEY == ""
