from __future__ import annotations

from app.core.config import Settings
from app.providers.weather.qweather import QWeatherProvider
from app.services.runtime_service import provider_capabilities


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_qweather_provider_fetch_known_city(monkeypatch):
    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append((url, params, headers, timeout))
        if url.endswith("/weather/now"):
            return _FakeResponse(
                {
                    "code": "200",
                    "now": {"temp": "33", "humidity": "61", "text": "多云", "obsTime": "2026-08-10T10:00+08:00"},
                }
            )
        raise AssertionError(url)

    monkeypatch.setattr("app.providers.weather.qweather.httpx.get", fake_get)

    provider = QWeatherProvider("https://geoapi.qweather.com/v2", "https://devapi.qweather.com/v7", "key")
    snapshot = provider.fetch("上海")

    assert provider.name == "qweather"
    assert snapshot.city == "上海"
    assert snapshot.temperature_c == 33.0
    assert snapshot.humidity_pct == 61.0
    assert snapshot.condition == "多云"
    assert len(calls) == 1
    assert calls[0][1]["location"] == "101020100"


def test_qweather_provider_fetch_lookup_city(monkeypatch):
    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append((url, params, headers, timeout))
        if url.endswith("/city/lookup"):
            return _FakeResponse({"code": "200", "location": [{"id": "101230201", "name": "厦门", "adm2": "厦门"}]})
        if url.endswith("/weather/now"):
            return _FakeResponse(
                {
                    "code": "200",
                    "now": {"temp": "31", "humidity": "70", "text": "晴", "obsTime": "2026-08-10T10:00+08:00"},
                }
            )
        raise AssertionError(url)

    monkeypatch.setattr("app.providers.weather.qweather.httpx.get", fake_get)

    provider = QWeatherProvider("https://geoapi.qweather.com/v2", "https://devapi.qweather.com/v7", "key")
    snapshot = provider.fetch("厦门")

    assert snapshot.city == "厦门"
    assert snapshot.temperature_c == 31.0
    assert snapshot.humidity_pct == 70.0
    assert snapshot.condition == "晴"
    assert len(calls) == 2


def test_qweather_runtime_capability_is_configured():
    settings = Settings(
        weather_provider="qweather",
        weather_api_key="weather-key",
        weather_city="上海",
    )

    capability = provider_capabilities(settings)["weather"]

    assert capability["provider"] == "qweather"
    assert capability["status"] == "configured"
    assert capability["is_simulated"] is False
