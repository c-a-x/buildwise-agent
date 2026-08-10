from __future__ import annotations

import json
from dataclasses import replace

import pytest

from app.core.config import settings
from app.models import WellbeingRecord
from app.providers.wellbeing import load_wellbeing_rules
from app.services.wellbeing_service import WellbeingService

ANALYZE_PAYLOAD = {
    "project_id": "PRJ-001",
    "temperature_c": 36,
    "humidity_pct": 60,
    "condition": "晴",
    "description": "一号楼西侧屋面钢筋绑扎作业面",
}


def _analyze(client, temperature_c: float, **overrides):
    from tests.conftest import login

    payload = {**ANALYZE_PAYLOAD, "temperature_c": temperature_c, **overrides}
    response = client.post("/api/v1/care/analyze", json=payload, headers=login(client, "manager"))
    assert response.status_code == 200
    return response.json()["data"]


# ---------- 规则库加载 ----------


def test_load_wellbeing_rules_shipped_library():
    rules = load_wellbeing_rules(settings.wellbeing_rules_path)
    assert rules.load_error == ""
    assert rules.version == "1.0"
    assert "89号" in rules.source
    assert len(rules.heat_levels) == 4
    assert len(rules.tips) >= 3
    assert len(rules.first_aid) == 3
    assert len(rules.facilities) >= 1
    assert "高温津贴" in rules.allowance


def test_load_wellbeing_rules_missing_file_falls_back(tmp_path):
    rules = load_wellbeing_rules(tmp_path / "missing.json")
    assert rules.load_error != ""
    assert rules.source == "内置兜底规则"
    assert rules.heat_level_for(40).level == "red"


def test_load_wellbeing_rules_bad_json_falls_back(tmp_path):
    broken = tmp_path / "rules.json"
    broken.write_text("{ not json", encoding="utf-8")
    rules = load_wellbeing_rules(broken)
    assert rules.load_error != ""
    assert len(rules.heat_levels) == 4


# ---------- 指标计算 ----------


def test_heat_level_thresholds():
    from app.providers.wellbeing import wellbeing_rules

    rules = wellbeing_rules()
    assert rules.heat_level_for(34.9).level == "none"
    assert rules.heat_level_for(35).level == "yellow"
    assert rules.heat_level_for(37).level == "orange"
    assert rules.heat_level_for(40).level == "red"


def test_risk_index_temperature_base_and_humidity_adjustment():
    # 温度基分：30℃→25、35℃→50、37℃→66、40℃→90、41℃→96
    assert WellbeingService._risk_index(30, 50) == 25
    assert WellbeingService._risk_index(35, 60) == 50
    assert WellbeingService._risk_index(37, 70) == 66
    assert WellbeingService._risk_index(40, 80) == 90
    assert WellbeingService._risk_index(41, 90) == 96
    # 湿度修正：>60% 加分、<40% 减分
    assert WellbeingService._risk_index(35, 80) > WellbeingService._risk_index(35, 60)
    assert WellbeingService._risk_index(35, 30) < WellbeingService._risk_index(35, 60)


def test_risk_index_monotonic_with_temperature():
    previous = -1
    for temperature in range(25, 46):
        current = WellbeingService._risk_index(temperature, 60)
        assert current >= previous
        previous = current


def test_risk_tier_boundaries():
    assert WellbeingService._risk_tier(29) == "低"
    assert WellbeingService._risk_tier(30) == "中"
    assert WellbeingService._risk_tier(49) == "中"
    assert WellbeingService._risk_tier(50) == "高"
    assert WellbeingService._risk_tier(74) == "高"
    assert WellbeingService._risk_tier(75) == "极高"


# ---------- 分析端点 ----------


def test_analyze_heat_levels_and_persists(client, db_session):
    for temperature, expected in [(34.9, "none"), (35, "yellow"), (37, "orange"), (40, "red")]:
        data = _analyze(client, temperature)
        assert data["heat_level"] == expected
        assert data["is_simulated"] is False  # 规则库正常加载

    red_row = db_session.query(WellbeingRecord).filter(WellbeingRecord.heat_level == "red").one()
    assert red_row.project_id == "PRJ-001"
    assert red_row.requested_by == "USR-001"
    assert red_row.is_simulated is False


def test_analyze_red_reminders_include_stop_work_and_allowance(client):
    data = _analyze(client, 41, humidity_pct=90)
    tip_ids = [tip["id"] for tip in data["reminders"]]
    assert "stop_work" in tip_ids
    assert "hydration" in tip_ids
    assert any("停止" in tip["text"] for tip in data["reminders"])
    assert data["risk_tier"] == "极高"
    assert "高温津贴" in data["allowance"]
    assert "怀孕女职工" in data["special_groups"]
    assert len(data["first_aid"]) == 3
    assert len(data["facilities"]) >= 1
    assert data["condition"] == "晴"


def test_analyze_uv_mapping_by_condition(client):
    assert _analyze(client, 36, condition="晴")["uv"] == "强"
    assert _analyze(client, 36, condition="多云")["uv"] == "中"
    assert _analyze(client, 36, condition="雷阵雨")["uv"] == "弱"


def test_analyze_denied_for_outsider(client, db_session):
    from app.core.security import hash_password
    from app.models import User
    from tests.conftest import login

    db_session.add(User(id="USR-999", username="outsider", real_name="非项目成员", role="safety_officer", password_hash=hash_password("BuildWise123!"), is_active=True))
    db_session.commit()
    response = client.post("/api/v1/care/analyze", json=ANALYZE_PAYLOAD, headers=login(client, "outsider"))
    assert response.status_code == 403


# ---------- 广播联动 ----------


def _enable_broadcast_webhook(monkeypatch):
    import app.api.v1.endpoints.wellbeing as wellbeing_endpoint
    import app.services.wellbeing_service as wellbeing_service_module

    webhook_settings = replace(settings, broadcast_webhook_url="http://test/broadcast")
    monkeypatch.setattr(wellbeing_endpoint, "settings", webhook_settings)
    monkeypatch.setattr(wellbeing_service_module, "default_settings", webhook_settings)
    calls: list[str] = []
    monkeypatch.setattr(wellbeing_endpoint, "broadcast_text_alert", lambda message, settings: calls.append(message))
    return calls


def test_red_heat_triggers_broadcast(client, monkeypatch):
    calls = _enable_broadcast_webhook(monkeypatch)
    data = _analyze(client, 41)
    assert data["broadcast"] is True
    assert len(calls) == 1
    assert "高温红色预警" in calls[0]


def test_non_red_heat_does_not_broadcast(client, monkeypatch):
    calls = _enable_broadcast_webhook(monkeypatch)
    data = _analyze(client, 35)
    assert data["broadcast"] is False
    assert calls == []


def test_red_heat_without_webhook_returns_broadcast_false(client):
    # 默认 settings.broadcast_webhook_url 为空：即使红色高温也不联动广播
    data = _analyze(client, 41)
    assert data["broadcast"] is False


# ---------- 历史记录 ----------


def test_records_list_and_detail_roundtrip(client):
    from tests.conftest import login

    headers = login(client, "manager")
    created = _analyze(client, 38)

    listing = client.get("/api/v1/care/records", headers=headers).json()["data"]
    assert any(item["analysis_id"] == created["analysis_id"] for item in listing)

    detail = client.get(f"/api/v1/care/records/{created['analysis_id']}", headers=headers).json()["data"]
    assert detail["heat_level"] == "orange"
    assert detail["project_name"] == "测试演示项目"
    assert len(detail["first_aid"]) == 3


def test_records_filter_by_project(client):
    from tests.conftest import login

    headers = login(client, "manager")
    _analyze(client, 36)
    listing = client.get("/api/v1/care/records?project_id=PRJ-001", headers=headers).json()["data"]
    assert all(item["project_id"] == "PRJ-001" for item in listing)


# ---------- 天气与提示 ----------


def test_weather_unconfigured_returns_available_false(client, monkeypatch):
    from app.core.config import settings
    from tests.conftest import login

    # 显式关闭天气 Provider：不依赖 .env 状态，也不发起真实网络请求
    import app.api.v1.endpoints.wellbeing as wellbeing_endpoint

    offline = replace(settings, weather_provider="off", weather_api_key="")
    monkeypatch.setattr(wellbeing_endpoint, "settings", offline)

    response = client.get("/api/v1/care/weather", headers=login(client, "manager"))
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["available"] is False
    assert "未配置天气 API" in data["reason"]
    assert data["is_simulated"] is True


def test_tips_returns_rule_library(client):
    from tests.conftest import login

    data = client.get("/api/v1/care/tips", headers=login(client, "manager")).json()["data"]
    assert data["version"] == "1.0"
    assert "89号" in data["source"]
    assert data["load_error"] == ""
    assert len(data["heat_levels"]) == 4
    assert len(data["first_aid"]) == 3


def test_status_available(client):
    from tests.conftest import login

    data = client.get("/api/v1/care/status", headers=login(client, "manager")).json()["data"]
    assert data["key"] == "care"
    assert data["status"] == "available"


# ---------- 鉴权 ----------


def test_analyze_requires_login(client):
    response = client.post("/api/v1/care/analyze", json=ANALYZE_PAYLOAD)
    assert response.status_code == 401


def test_weather_requires_login(client):
    assert client.get("/api/v1/care/weather").status_code == 401


def test_tips_requires_login(client):
    assert client.get("/api/v1/care/tips").status_code == 401


def test_weather_provider_openweather_condition_map():
    from app.providers.weather.openweather import _CONDITION_MAP, OpenWeatherProvider

    provider = OpenWeatherProvider("http://x", "key")
    assert provider.name == "openweather"
    assert _CONDITION_MAP["Clear"] == "晴"
    assert _CONDITION_MAP["Clouds"] == "多云"
    assert _CONDITION_MAP["Thunderstorm"] == "雷阵雨"
    assert _CONDITION_MAP["Rain"] == "小雨"


def test_weather_provider_qweather_location_ids_and_attrs():
    from app.providers.weather.qweather import QWeatherProvider

    provider = QWeatherProvider("https://api.qweather.com/v7", "key")
    assert provider.name == "qweather"
    assert provider.is_simulated is False
    # 未收录城市原样透传（可配经纬度或 LocationID），中文城市名映射到官方 LocationID
    assert provider._location_id("北京") == "101010100"
    assert provider._location_id("beijing") == "101010100"
    assert provider._location_id("30.5,114.3") == "30.5,114.3"


def test_weather_provider_qweather_fetch_parses_response(monkeypatch):
    from datetime import datetime, timedelta, timezone

    from app.providers.weather.qweather import QWeatherProvider

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "code": "200",
                "updateTime": "2026-08-10T15:35+08:00",
                "now": {"temp": "33", "humidity": "71", "text": "多云"},
            }

    calls: list[tuple[str, dict[str, object]]] = []
    import httpx

    def _fake_get(url, params, timeout):
        calls.append((url, params))
        return _FakeResponse()

    monkeypatch.setattr(httpx, "get", _fake_get)
    snapshot = QWeatherProvider("https://api.qweather.com/v7", "k").fetch("beijing")
    assert snapshot.temperature_c == 33.0
    assert snapshot.humidity_pct == 71.0
    assert snapshot.condition == "多云"
    assert snapshot.city == "beijing"
    assert isinstance(snapshot.observed_at, datetime)
    assert snapshot.observed_at.utcoffset() == timezone(timedelta(hours=8)).utcoffset(None)
    assert calls[0][1]["location"] == "101010100"
    assert calls[0][1]["key"] == "k"
    assert calls[0][0] == "https://api.qweather.com/v7/weather/now"


def test_weather_provider_qweather_fetch_bad_update_time_falls_back(monkeypatch):
    from datetime import datetime

    from app.providers.weather.qweather import QWeatherProvider

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"code": "200", "updateTime": "not-a-date", "now": {"temp": "28", "humidity": "60", "text": "晴"}}

    import httpx

    monkeypatch.setattr(httpx, "get", lambda url, params, timeout: _FakeResponse())
    snapshot = QWeatherProvider("https://api.qweather.com/v7", "k").fetch("北京")
    assert isinstance(snapshot.observed_at, datetime)


def test_weather_provider_qweather_fetch_invalid_code(monkeypatch):
    from app.core.exceptions import AppError
    from app.providers.weather.qweather import QWeatherProvider

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"code": "401", "error": {"title": "apikey 无效"}}

    import httpx

    monkeypatch.setattr(httpx, "get", lambda url, params, timeout: _FakeResponse())
    with pytest.raises(AppError) as exc_info:
        QWeatherProvider("https://api.qweather.com/v7", "k").fetch("北京")
    assert exc_info.value.code == "WEATHER_INVALID_RESPONSE"


def test_broadcast_text_alert_noop_without_webhook():
    from app.services.broadcast_service import broadcast_text_alert

    # 未配置 webhook 时不抛错、不发请求（无断言即通过）
    broadcast_text_alert("高温红色预警！", settings)
