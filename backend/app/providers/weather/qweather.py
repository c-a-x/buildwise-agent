from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.exceptions import AppError
from app.providers.weather.base import DailyForecast, WeatherSnapshot


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

CITY_NAMES: tuple[str, ...] = tuple(
    sorted({key for key in _CITY_LOCATION_IDS if any(ord(char) > 127 for char in key)})
)


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


class QWeatherProvider:
    """和风天气实时天气与当日预报 Provider。"""

    name = "qweather"
    is_simulated = False

    def __init__(self, geo_base_url: str, weather_base_url: str, api_key: str, auth_type: str = "query") -> None:
        self.geo_base_url = geo_base_url.rstrip("/")
        self.weather_base_url = weather_base_url.rstrip("/")
        self.api_key = api_key
        self.auth_type = auth_type.strip().lower() or "query"

    def fetch(self, city: str) -> WeatherSnapshot:
        if not city:
            raise AppError("未指定查询城市", "WEATHER_CITY_MISSING", 400)

        location_id, resolved_city = self._resolve_location(city)
        payload = self._request_json(f"{self.weather_base_url}/weather/now", {"location": location_id})
        if str(payload.get("code") or "") != "200":
            raise AppError(f"和风天气接口返回异常状态：{payload.get('code')}", "WEATHER_INVALID_RESPONSE", 502)

        now = payload.get("now") or {}
        try:
            temperature_c = float(now["temp"])
            humidity_pct = float(now["humidity"])
        except (KeyError, TypeError, ValueError) as exc:
            raise AppError("和风天气接口返回数据不完整", "WEATHER_INVALID_RESPONSE", 502) from exc
        condition = str(now.get("text") or "").strip() or "晴"
        observed_at = _parse_datetime(now.get("obsTime") or payload.get("updateTime"))
        return WeatherSnapshot(
            temperature_c=temperature_c,
            humidity_pct=humidity_pct,
            condition=condition,
            city=resolved_city,
            observed_at=observed_at,
        )

    def fetch_daily_forecast(self, city: str) -> DailyForecast:
        if not city:
            raise AppError("未指定查询城市", "WEATHER_CITY_MISSING", 400)

        location_id, _resolved_city = self._resolve_location(city)
        payload = self._request_json(f"{self.weather_base_url}/weather/3d", {"location": location_id})
        if str(payload.get("code") or "") != "200":
            raise AppError(f"和风天气接口返回异常状态：{payload.get('code')}", "WEATHER_INVALID_RESPONSE", 502)

        daily = payload.get("daily")
        if not isinstance(daily, list) or not daily:
            raise AppError("和风天气接口返回预报数据为空", "WEATHER_INVALID_RESPONSE", 502)
        today = daily[0] or {}
        try:
            temp_max_c = float(today["tempMax"])
            temp_min_c = float(today["tempMin"])
            humidity_pct = float(today["humidity"])
        except (KeyError, TypeError, ValueError) as exc:
            raise AppError("和风天气接口返回预报数据不完整", "WEATHER_INVALID_RESPONSE", 502) from exc
        return DailyForecast(
            fx_date=str(today.get("fxDate") or ""),
            temp_max_c=temp_max_c,
            temp_min_c=temp_min_c,
            condition_day=str(today.get("textDay") or "晴"),
            humidity_pct=humidity_pct,
            uv_index=str(today.get("uvIndex") or ""),
        )

    def _resolve_location(self, city: str) -> tuple[str, str]:
        normalized = city.strip()
        mapped = _CITY_LOCATION_IDS.get(normalized.lower())
        if mapped:
            return mapped, normalized
        if normalized.isdigit() or "," in normalized:
            return normalized, normalized

        payload = self._request_json(f"{self.geo_base_url}/city/lookup", {"location": normalized})
        if str(payload.get("code") or "") != "200":
            raise AppError(f"和风天气城市查询失败：{payload.get('code')}", "WEATHER_CITY_LOOKUP_FAILED", 502)

        locations = payload.get("location") or []
        if not locations:
            raise AppError(f"和风天气未找到城市：{city}", "WEATHER_CITY_NOT_FOUND", 404)
        location = locations[0] or {}
        location_id = str(location.get("id") or "").strip()
        if not location_id:
            raise AppError("和风天气城市记录缺少 location id", "WEATHER_CITY_NOT_FOUND", 404)

        resolved_city = str(location.get("name") or normalized).strip()
        parent = str(location.get("adm2") or "").strip()
        if parent and parent != resolved_city:
            resolved_city = f"{parent} · {resolved_city}"
        return location_id, resolved_city

    def _request_json(self, url: str, params: dict[str, str]) -> dict[str, Any]:
        request_params = dict(params)
        headers: dict[str, str] = {}
        if self.auth_type == "bearer":
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif self.auth_type == "header":
            headers["X-QW-Api-Key"] = self.api_key
        else:
            request_params["key"] = self.api_key
        try:
            response = httpx.get(url, params=request_params, headers=headers, timeout=8.0)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 403:
                raise AppError(
                    "和风天气接口返回 403：请确认 API Host、认证方式 WEATHER_AUTH_TYPE 和 API key 状态。",
                    "WEATHER_AUTH_FAILED",
                    502,
                ) from exc
            raise AppError(
                f"和风天气接口请求失败：HTTP {exc.response.status_code}",
                "WEATHER_FETCH_FAILED",
                502,
            ) from exc
        except (httpx.HTTPError, OSError, ValueError) as exc:
            raise AppError("和风天气接口请求失败：网络或返回格式异常", "WEATHER_FETCH_FAILED", 502) from exc
        if not isinstance(payload, dict):
            raise AppError("和风天气接口返回格式错误", "WEATHER_INVALID_RESPONSE", 502)
        return payload
