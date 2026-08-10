"""工友关怀定时调度：每天按预报日最高气温自动评估高温等级并写入关怀历史。

- `run_scheduled_care`：同步、可直接单测；从天气 Provider 取当日最高气温预报 → 按
  规则库评估高温等级 → 写入一条 `auto=true` 的关怀记录（归属默认项目，requested_by=None）；
  橙/红色高温且配置了广播 webhook 时推送语音播报（失败静默）。
- `care_scheduler_loop`：异步后台任务，在 `CARE_SCHEDULE_TIME` 触发一次/天（用
  `last_run.date` 防同一天重复触发），由 main.py 的 lifespan 启停。
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings, settings as default_settings
from app.core.exceptions import AppError
from app.db.session import SessionLocal
from app.models import Project
from app.providers.factory import build_weather_provider
from app.providers.weather.qweather import QWeatherProvider
from app.schemas.wellbeing import WeatherSourceRead
from app.services.broadcast_service import broadcast_text_alert
from app.services.wellbeing_service import WellbeingService, broadcast_message

logger = logging.getLogger("buildwise")

# 最近一次执行结果（供 /care/status 展示）
last_run: dict[str, Any] = {}


@dataclass(frozen=True)
class ScheduledCareResult:
    """一次定时关怀的执行结果。skipped=True 表示未生成记录（未配置 Provider/城市/项目或请求失败）。"""

    skipped: bool
    reason: str | None = None
    heat_level: str | None = None
    project_id: str | None = None
    broadcast: bool = False
    city: str | None = None


def run_scheduled_care(db: Session, runtime_settings: Settings | None = None) -> ScheduledCareResult:
    """执行一次定时关怀（同步）：预报日最高气温 → 高温等级 → 关怀记录（+ 橙色/红色广播）。

    任何天气请求失败只标记 skipped，绝不抛异常中断调度循环。
    """
    s = runtime_settings or default_settings
    provider = build_weather_provider(s)
    if not isinstance(provider, QWeatherProvider):
        return ScheduledCareResult(skipped=True, reason="未配置支持预报的天气 Provider（需 qweather）")
    city = (s.care_schedule_city or s.weather_city).strip()
    if not city:
        return ScheduledCareResult(skipped=True, reason="未指定定时关怀城市（CARE_SCHEDULE_CITY 或 WEATHER_CITY）")
    try:
        forecast = provider.fetch_daily_forecast(city)
    except AppError as exc:
        return ScheduledCareResult(skipped=True, reason=f"获取天气预报失败：{exc}")
    project = db.query(Project).order_by(Project.created_at.desc()).first()
    if not project:
        return ScheduledCareResult(skipped=True, reason="无默认项目可归属关怀记录")
    response = WellbeingService(db, s).analyze(
        project_id=project.id,
        temperature_c=forecast.temp_max_c,
        humidity_pct=forecast.humidity_pct,
        condition=forecast.condition_day,
        description=f"系统定时关怀（{city} 天气预报，日最高气温 {forecast.temp_max_c:.0f}℃）",
        requested_by=None,
        auto=True,
        broadcast_threshold="orange",
        weather_source=WeatherSourceRead(city=city, provider=provider.name, observed_at=forecast.fx_date),
    )
    if response.broadcast:
        broadcast_text_alert(broadcast_message(response), s)
    return ScheduledCareResult(
        skipped=False,
        heat_level=response.heat_level,
        project_id=project.id,
        broadcast=response.broadcast,
        city=city,
    )


def _refresh_last_run(result: ScheduledCareResult) -> None:
    last_run.update(
        {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M"),
            "heat_level": result.heat_level,
            "project_id": result.project_id,
            "broadcast": result.broadcast,
            "city": result.city,
            "reason": result.reason,
        }
    )


async def care_scheduler_loop(s: Settings | None = None) -> None:
    """后台定时循环：每日在 CARE_SCHEDULE_TIME 触发一次 run_scheduled_care。"""
    runtime = s or default_settings
    while True:
        now = datetime.now()
        if now.strftime("%H:%M") == runtime.care_schedule_time and last_run.get("date") != now.strftime("%Y-%m-%d"):
            logger.info("定时关怀触发：城市=%s", runtime.care_schedule_city or runtime.weather_city)
            db = SessionLocal()
            try:
                result = await asyncio.to_thread(run_scheduled_care, db, runtime)
                _refresh_last_run(result)
                logger.info("定时关怀完成：%s", result)
            finally:
                db.close()
        await asyncio.sleep(30)
