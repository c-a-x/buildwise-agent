from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.core.exceptions import AppError
from app.providers.weather.base import WeatherSnapshot

# OpenWeather weather.main → 中文天气描述
_CONDITION_MAP = {
    "Clear": "晴",
    "Clouds": "多云",
    "Mist": "阴",
    "Fog": "雾",
    "Haze": "阴",
    "Smoke": "阴",
    "Dust": "扬尘",
    "Sand": "扬尘",
    "Drizzle": "小雨",
    "Rain": "小雨",
    "Thunderstorm": "雷阵雨",
    "Snow": "中雪",
    "Squall": "雷阵雨",
    "Tornado": "雷阵雨",
    "Extreme": "雷阵雨",
}


class OpenWeatherProvider:
    """OpenWeather 兼容 API 的 Current weather 实时天气 Provider。"""

    name = "openweather"
    is_simulated = False

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def fetch(self, city: str) -> WeatherSnapshot:
        if not city:
            raise AppError("未指定查询城市", "WEATHER_CITY_MISSING", 400)
        try:
            response = httpx.get(
                f"{self.base_url}/weather",
                params={"q": city, "appid": self.api_key, "units": "metric", "lang": "zh_cn"},
                timeout=8.0,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, OSError, ValueError) as exc:
            raise AppError(f"天气接口请求失败：{exc}", "WEATHER_FETCH_FAILED", 502) from exc
        main = payload.get("main") or {}
        weather_list = payload.get("weather") or []
        temperature_c = main.get("temp")
        humidity_pct = main.get("humidity")
        if temperature_c is None or humidity_pct is None:
            raise AppError("天气接口返回数据不完整", "WEATHER_INVALID_RESPONSE", 502)
        code = str(weather_list[0].get("main", "")) if weather_list else ""
        return WeatherSnapshot(
            temperature_c=float(temperature_c),
            humidity_pct=float(humidity_pct),
            condition=_CONDITION_MAP.get(code, "晴"),
            city=str(payload.get("name") or city),
            observed_at=datetime.now(timezone.utc),
        )
