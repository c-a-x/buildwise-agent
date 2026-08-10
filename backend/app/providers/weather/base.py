from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class WeatherSnapshot:
    """一次实时天气快照（工友关怀用于预填高温分析）。"""

    temperature_c: float
    humidity_pct: float
    condition: str  # 晴 / 多云 / 阴 / 小雨 …
    city: str
    observed_at: datetime
    is_simulated: bool = False


@dataclass(frozen=True)
class DailyForecast:
    """当日天气预报快照（工友关怀定时关怀按日最高气温评估高温等级）。"""

    fx_date: str  # 预报日期，如 2026-08-10
    temp_max_c: float  # 日最高气温
    temp_min_c: float  # 日最低气温
    condition_day: str  # 白天天气现象：晴 / 多云 …
    humidity_pct: float  # 相对湿度
    uv_index: str  # 紫外线指数（0~11+）


class WeatherProvider(Protocol):
    """实时天气数据源（可选增强）。未配置 Provider 时工友关怀回退手动输入。"""

    name: str
    is_simulated: bool

    def fetch(self, city: str) -> WeatherSnapshot:
        """按城市拉取当前天气；失败抛 AppError，由服务层降级。"""
        ...
