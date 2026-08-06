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


class WeatherProvider(Protocol):
    """实时天气数据源（可选增强）。未配置 Provider 时工友关怀回退手动输入。"""

    name: str
    is_simulated: bool

    def fetch(self, city: str) -> WeatherSnapshot:
        """按城市拉取当前天气；失败抛 AppError，由服务层降级。"""
        ...
