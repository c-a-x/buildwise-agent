from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.core.exceptions import AppError
from app.providers.weather.base import DailyForecast, WeatherSnapshot

# 常见施工城市 → QWeather LocationID（官方城市代码）。未收录的城市可配经纬度 "经度,纬度" 或直接填 LocationID。
_CITY_LOCATION_IDS: dict[str, str] = {
    "beijing": "101010100",
    "北京": "101010100",
    "shanghai": "101020100",
    "上海": "101020100",
    "guangzhou": "101280101",
    "广州": "101280101",
    "shenzhen": "101280601",
    "深圳": "101280601",
    "hangzhou": "101210101",
    "杭州": "101210101",
    "nanjing": "101190101",
    "南京": "101190101",
    "chengdu": "101270101",
    "成都": "101270101",
    "wuhan": "101200101",
    "武汉": "101200101",
    "xian": "101110101",
    "西安": "101110101",
    "chongqing": "101040100",
    "重庆": "101040100",
    "tianjin": "101030100",
    "天津": "101030100",
    "suzhou": "101190401",
    "苏州": "101190401",
    "sanya": "101310201",
    "三亚": "101310201",
}

# 城市下拉候选：取 _CITY_LOCATION_IDS 中的中文城市名（供工友关怀页面选择查询城市）。
CITY_NAMES: tuple[str, ...] = tuple(sorted({key for key in _CITY_LOCATION_IDS if any(ord(char) > 127 for char in key)}))


class QWeatherProvider:
    """和风天气（QWeather）实时天气 Provider。

    QWeather 2026 年起使用账号专属 API Host（控制台「开发者信息」查看，
    形如 https://xxxxx.re.qweatherapi.com），base_url 需包含路径版本，如 .../v7。
    """

    name = "qweather"
    is_simulated = False

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    @staticmethod
    def _location_id(location: str) -> str:
        """解析查询城市 → QWeather LocationID：优先官方城市代码映射，未收录的原样透传（可配经纬度或 LocationID）。"""
        return _CITY_LOCATION_IDS.get(location.lower()) or location

    def _get_payload(self, path: str, params: dict[str, str]) -> dict[str, object]:
        """请求 QWeather API 并统一校验：网络/解析失败或业务错误码均转 AppError。"""
        try:
            response = httpx.get(
                f"{self.base_url}{path}",
                params={"key": self.api_key, **params},
                timeout=8.0,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, OSError, ValueError) as exc:
            raise AppError(f"天气接口请求失败：{exc}", "WEATHER_FETCH_FAILED", 502) from exc
        code = str(payload.get("code", ""))
        if code != "200":
            detail = payload.get("error") or {}
            title = str(detail.get("title", code))
            raise AppError(f"天气接口返回错误：{title}", "WEATHER_INVALID_RESPONSE", 502)
        return payload

    def fetch(self, location: str) -> WeatherSnapshot:
        if not location:
            raise AppError("未指定查询城市", "WEATHER_CITY_MISSING", 400)
        payload = self._get_payload("/weather/now", {"location": self._location_id(location)})
        now = payload.get("now") or {}
        try:
            temperature_c = float(now["temp"])
            humidity_pct = float(now["humidity"])
        except (KeyError, TypeError, ValueError) as exc:
            raise AppError("天气接口返回数据不完整", "WEATHER_INVALID_RESPONSE", 502) from exc
        try:
            observed_at = datetime.fromisoformat(str(payload.get("updateTime") or ""))
        except ValueError:
            observed_at = datetime.now(timezone.utc)
        return WeatherSnapshot(
            temperature_c=temperature_c,
            humidity_pct=humidity_pct,
            condition=str(now.get("text") or "晴"),
            city=str(location),
            observed_at=observed_at,
        )

    def fetch_daily_forecast(self, location: str) -> DailyForecast:
        """当日天气预报（3 天预报取第 1 天）：工友关怀定时关怀按日最高气温评估高温等级。"""
        if not location:
            raise AppError("未指定查询城市", "WEATHER_CITY_MISSING", 400)
        payload = self._get_payload("/weather/3d", {"location": self._location_id(location)})
        daily = payload.get("daily")
        if not isinstance(daily, list) or not daily:
            raise AppError("天气接口返回预报数据为空", "WEATHER_INVALID_RESPONSE", 502)
        today = daily[0]
        try:
            temp_max_c = float(today["tempMax"])
            temp_min_c = float(today["tempMin"])
            humidity_pct = float(today["humidity"])
        except (KeyError, TypeError, ValueError) as exc:
            raise AppError("天气接口返回预报数据不完整", "WEATHER_INVALID_RESPONSE", 502) from exc
        return DailyForecast(
            fx_date=str(today.get("fxDate") or ""),
            temp_max_c=temp_max_c,
            temp_min_c=temp_min_c,
            condition_day=str(today.get("textDay") or "晴"),
            humidity_pct=humidity_pct,
            uv_index=str(today.get("uvIndex") or ""),
        )
