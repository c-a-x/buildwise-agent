from __future__ import annotations

from dataclasses import replace

import pytest

from app.core.config import settings
from app.core.exceptions import AppError
from app.models import WellbeingRecord
from app.providers.weather.base import DailyForecast
from app.providers.weather.qweather import QWeatherProvider

ANALYZE_PAYLOAD = {
    "project_id": "PRJ-001",
    "temperature_c": 36,
    "humidity_pct": 60,
    "condition": "晴",
    "description": "一号楼西侧屋面钢筋绑扎作业面",
}


# ---------- QWeather 预报（fetch_daily_forecast） ----------


def _forecast_response(daily: list[dict[str, str]]) -> dict[str, object]:
    return {"code": "200", "daily": daily}


def test_fetch_daily_forecast_parses(monkeypatch):
    import httpx

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return _forecast_response(
                [{"fxDate": "2026-08-10", "tempMax": "33", "tempMin": "24", "textDay": "多云", "humidity": "74", "uvIndex": "9"}]
            )

    monkeypatch.setattr(httpx, "get", lambda url, params=None, headers=None, timeout=None: _FakeResponse())
    forecast = QWeatherProvider("https://geo.qweather.com/v2", "https://api.qweather.com/v7", "k").fetch_daily_forecast("beijing")
    assert forecast.fx_date == "2026-08-10"
    assert forecast.temp_max_c == 33.0
    assert forecast.temp_min_c == 24.0
    assert forecast.condition_day == "多云"
    assert forecast.humidity_pct == 74.0
    assert forecast.uv_index == "9"


def test_fetch_daily_forecast_invalid_code(monkeypatch):
    import httpx

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"code": "401", "error": {"title": "apikey 无效"}}

    monkeypatch.setattr(httpx, "get", lambda url, params=None, headers=None, timeout=None: _FakeResponse())
    with pytest.raises(AppError) as exc_info:
        QWeatherProvider("https://geo.qweather.com/v2", "https://api.qweather.com/v7", "k").fetch_daily_forecast("北京")
    assert exc_info.value.code == "WEATHER_INVALID_RESPONSE"


def test_fetch_daily_forecast_empty_daily(monkeypatch):
    import httpx

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return _forecast_response([])

    monkeypatch.setattr(httpx, "get", lambda url, params=None, headers=None, timeout=None: _FakeResponse())
    with pytest.raises(AppError):
        QWeatherProvider("https://geo.qweather.com/v2", "https://api.qweather.com/v7", "k").fetch_daily_forecast("北京")


def test_fetch_daily_forecast_missing_fields(monkeypatch):
    import httpx

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return _forecast_response([{"fxDate": "2026-08-10", "textDay": "晴"}])

    monkeypatch.setattr(httpx, "get", lambda url, params=None, headers=None, timeout=None: _FakeResponse())
    with pytest.raises(AppError) as exc_info:
        QWeatherProvider("https://geo.qweather.com/v2", "https://api.qweather.com/v7", "k").fetch_daily_forecast("北京")
    assert exc_info.value.code == "WEATHER_INVALID_RESPONSE"


# ---------- 城市下拉 ----------


def test_cities_requires_login(client):
    assert client.get("/api/v1/care/cities").status_code == 401


def test_cities_lists_supported_cities(client):
    from tests.conftest import login

    data = client.get("/api/v1/care/cities", headers=login(client, "manager")).json()["data"]
    names = [item["name"] for item in data["cities"]]
    assert "北京" in names
    assert "上海" in names


# ---------- 分析带天气来源 ----------


def test_analyze_with_city_persists_weather_source(client, db_session):
    from tests.conftest import login

    payload = {**ANALYZE_PAYLOAD, "city": "北京"}
    response = client.post("/api/v1/care/analyze", json=payload, headers=login(client, "manager"))
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["weather_source"] == {"city": "北京", "provider": None, "observed_at": None}

    record = db_session.query(WellbeingRecord).order_by(WellbeingRecord.created_at.desc()).first()
    assert record.result_json["weather_source"] == {"city": "北京", "provider": None, "observed_at": None}
    assert record.result_json["auto"] is False


def test_analyze_without_city_has_null_weather_source(client):
    from tests.conftest import login

    response = client.post("/api/v1/care/analyze", json=ANALYZE_PAYLOAD, headers=login(client, "manager"))
    assert response.status_code == 200
    assert response.json()["data"]["weather_source"] is None


# ---------- 定时关怀调度 ----------


def _scheduled_settings(**overrides):
    return replace(
        settings,
        weather_provider="qweather",
        weather_city="beijing",
        broadcast_webhook_url="http://test/broadcast",
        **overrides,
    )


def _install_forecast_provider(monkeypatch, temp_max_c: float):
    import app.services.care_scheduler as scheduler_module

    provider = QWeatherProvider("https://geo.x/v2", "https://x/v7", "k")
    monkeypatch.setattr(
        provider,
        "fetch_daily_forecast",
        lambda location: DailyForecast(
            fx_date="2026-08-10",
            temp_max_c=temp_max_c,
            temp_min_c=24.0,
            condition_day="晴",
            humidity_pct=60.0,
            uv_index="9",
        ),
    )
    monkeypatch.setattr(scheduler_module, "build_weather_provider", lambda runtime: provider)
    return provider


def test_scheduled_care_red_heat_broadcasts_and_persists(client, db_session, monkeypatch):
    import app.services.care_scheduler as scheduler_module

    calls: list[str] = []
    monkeypatch.setattr(scheduler_module, "broadcast_text_alert", lambda message, runtime: calls.append(message))
    _install_forecast_provider(monkeypatch, 41)

    result = scheduler_module.run_scheduled_care(db_session, _scheduled_settings())
    assert result.skipped is False
    assert result.heat_level == "red"
    assert result.broadcast is True
    assert result.project_id == "PRJ-001"
    assert result.city == "beijing"
    assert len(calls) == 1
    assert "高温红色预警" in calls[0]

    records = db_session.query(WellbeingRecord).all()
    assert len(records) == 1
    record = records[0]
    assert record.requested_by is None  # 系统自动，非具体工友
    assert record.heat_level == "red"
    assert record.project_id == "PRJ-001"
    assert record.result_json["auto"] is True
    assert record.result_json["description"].startswith("系统定时关怀")
    assert record.result_json["weather_source"]["city"] == "beijing"
    assert record.result_json["weather_source"]["observed_at"] == "2026-08-10"


def test_scheduled_care_orange_heat_broadcasts(monkeypatch, db_session):
    import app.services.care_scheduler as scheduler_module

    calls: list[str] = []
    monkeypatch.setattr(scheduler_module, "broadcast_text_alert", lambda message, runtime: calls.append(message))
    _install_forecast_provider(monkeypatch, 38)

    result = scheduler_module.run_scheduled_care(db_session, _scheduled_settings())
    assert result.skipped is False
    assert result.heat_level == "orange"
    assert result.broadcast is True  # 定时关怀按预报日最高气温用橙档（≥37℃）即预警
    assert len(calls) == 1
    assert "高温橙色预警" in calls[0]


def test_scheduled_care_red_heat_triggers_buzzer(monkeypatch, db_session):
    import app.services.care_scheduler as scheduler_module

    buzzer_calls: list[tuple[str, str | None]] = []
    monkeypatch.setattr(scheduler_module, "notify_hard_alert", lambda hazards, url, message=None: buzzer_calls.append((url, message)))
    _install_forecast_provider(monkeypatch, 41)

    result = scheduler_module.run_scheduled_care(db_session, replace(_scheduled_settings(), alert_webhook_url="http://test/buzzer"))
    assert result.broadcast is True
    assert result.buzzer is True
    assert len(buzzer_calls) == 1
    assert buzzer_calls[0][0] == "http://test/buzzer"
    assert "高温红色预警" in (buzzer_calls[0][1] or "")


def test_scheduled_care_none_heat_does_not_trigger_buzzer(monkeypatch, db_session):
    import app.services.care_scheduler as scheduler_module

    buzzer_calls: list[tuple[str, str | None]] = []
    monkeypatch.setattr(scheduler_module, "notify_hard_alert", lambda hazards, url, message=None: buzzer_calls.append((url, message)))
    _install_forecast_provider(monkeypatch, 28)

    result = scheduler_module.run_scheduled_care(db_session, replace(_scheduled_settings(), alert_webhook_url="http://test/buzzer"))
    assert result.buzzer is False
    assert buzzer_calls == []


def test_scheduled_care_none_heat_persists_without_broadcast(monkeypatch, db_session):
    import app.services.care_scheduler as scheduler_module

    calls: list[str] = []
    monkeypatch.setattr(scheduler_module, "broadcast_text_alert", lambda message, runtime: calls.append(message))
    _install_forecast_provider(monkeypatch, 28)

    result = scheduler_module.run_scheduled_care(db_session, _scheduled_settings())
    assert result.skipped is False
    assert result.heat_level == "none"
    assert result.broadcast is False
    assert calls == []

    records = db_session.query(WellbeingRecord).all()
    assert len(records) == 1
    assert records[0].heat_level == "none"
    assert records[0].result_json["auto"] is True


def test_scheduled_care_without_provider_skips(client, db_session, monkeypatch):
    import app.services.care_scheduler as scheduler_module

    monkeypatch.setattr(scheduler_module, "build_weather_provider", lambda runtime: None)
    result = scheduler_module.run_scheduled_care(db_session, _scheduled_settings())
    assert result.skipped is True
    assert "天气 Provider" in (result.reason or "")
    assert db_session.query(WellbeingRecord).count() == 0


def test_scheduled_care_without_city_skips(monkeypatch, db_session):
    import app.services.care_scheduler as scheduler_module

    _install_forecast_provider(monkeypatch, 33)
    result = scheduler_module.run_scheduled_care(db_session, replace(_scheduled_settings(), weather_city="", care_schedule_city=""))
    assert result.skipped is True
    assert "城市" in (result.reason or "")
    assert db_session.query(WellbeingRecord).count() == 0


# ---------- 状态含定时信息 ----------


def test_status_includes_schedule(client, monkeypatch):
    import app.api.v1.endpoints.wellbeing as wellbeing_endpoint
    from tests.conftest import login

    scheduled = replace(settings, care_schedule_enabled=True, care_schedule_time="07:30", weather_city="beijing")
    monkeypatch.setattr(wellbeing_endpoint, "settings", scheduled)

    data = client.get("/api/v1/care/status", headers=login(client, "manager")).json()["data"]
    assert data["schedule"]["enabled"] is True
    assert data["schedule"]["time"] == "07:30"
    assert data["schedule"]["city"] == "beijing"
    assert "/api/v1/care/cities" in str(data["available_endpoints"])
