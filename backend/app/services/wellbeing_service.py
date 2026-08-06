from __future__ import annotations

import math
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import Settings, settings as default_settings
from app.core.exceptions import AppError, NotFoundError
from app.models import Project, WellbeingRecord
from app.providers.factory import build_weather_provider
from app.providers.wellbeing import WellbeingRules, wellbeing_rules
from app.schemas.wellbeing import (
    FacilityRead,
    FirstAidStageRead,
    HeatLevelRead,
    WellbeingAnalysisResponse,
    WellbeingRecordSummary,
    WellbeingTips,
    WellbeingTipRead,
    WeatherRead,
)
from app.utils.ids import new_id


class WellbeingService:
    """工友关怀核心：天气/环境输入 → 高温等级 + 中暑风险 + 温馨提醒。

    复刻 green/carbon 的表单输入 + 规则引擎模式，不走图像/五 Agent。
    规则库缺失时回退内置兜底规则并标记 is_simulated=true。
    """

    def __init__(self, db: Session, runtime_settings: Settings | None = None) -> None:
        self.db = db
        self.settings = runtime_settings or default_settings

    def analyze(
        self,
        *,
        project_id: str,
        temperature_c: float,
        humidity_pct: float,
        condition: str,
        description: str,
        requested_by: str,
    ) -> WellbeingAnalysisResponse:
        rules = wellbeing_rules()
        is_simulated = bool(rules.load_error)

        heat_level = rules.heat_level_for(temperature_c)
        risk_index = self._risk_index(temperature_c, humidity_pct)
        heat_index = self._heat_index(temperature_c, humidity_pct)
        uv = rules.condition_uv.get(condition.strip() or "晴", "中")
        restriction = rules.restriction.get(heat_level.level, "")
        broadcast = heat_level.level == "red" and bool(self.settings.broadcast_webhook_url)

        reminders = [
            WellbeingTipRead(id=f"level_{heat_level.level}", text=heat_level.advice)
        ] if heat_level.level != "none" and heat_level.advice else []
        reminders.extend(
            WellbeingTipRead(id=tip.id, text=tip.text)
            for tip in rules.tips_for(heat_level.level)
        )

        first_aid = [FirstAidStageRead(**vars(stage)) for stage in rules.first_aid]
        facilities = [FacilityRead(**vars(item)) for item in rules.facilities]

        record = WellbeingRecord(
            id=new_id("WB"),
            project_id=project_id,
            requested_by=requested_by,
            heat_level=heat_level.level,
            heat_index=heat_index,
            risk_index=risk_index,
            is_simulated=is_simulated,
            result_json={
                "temperature_c": temperature_c,
                "humidity_pct": humidity_pct,
                "condition": condition,
                "description": description,
                "heat_level": heat_level.level,
                "heat_level_name": heat_level.name,
                "advice": heat_level.advice,
                "restriction": restriction,
                "risk_index": risk_index,
                "risk_tier": self._risk_tier(risk_index),
                "heat_index": heat_index,
                "uv": uv,
                "reminders": [tip.model_dump() for tip in reminders],
                "allowance": rules.allowance,
                "special_groups": rules.special_groups,
                "first_aid": [stage.model_dump() for stage in first_aid],
                "facilities": [item.model_dump() for item in facilities],
                "broadcast": broadcast,
                "source": rules.source,
                "rules_version": rules.version,
            },
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return self._response(record, rules)

    def list_records(self, project_id: str | None = None) -> list[WellbeingRecordSummary]:
        query = self.db.query(WellbeingRecord)
        if project_id:
            query = query.filter(WellbeingRecord.project_id == project_id)
        records = query.order_by(WellbeingRecord.created_at.desc()).all()
        return [self._summary(record) for record in records]

    def get_record(self, record_id: str) -> WellbeingAnalysisResponse:
        record = self.db.get(WellbeingRecord, record_id)
        if not record:
            raise NotFoundError("关怀分析不存在", "WELLBEING_RECORD_NOT_FOUND")
        return self._response(record, wellbeing_rules())

    def weather(self, city: str | None = None) -> WeatherRead:
        """实时天气查询；未配置 Provider 或请求失败时返回 available=false（不抛错）。"""
        provider = build_weather_provider(self.settings)
        if provider is None:
            return WeatherRead(
                available=False,
                reason="未配置天气 API（WEATHER_PROVIDER/WEATHER_API_KEY），请在页面手动输入",
                provider=None,
                is_simulated=True,
            )
        query_city = city or self.settings.weather_city
        if not query_city:
            return WeatherRead(
                available=False,
                reason="未指定查询城市（WEATHER_CITY 或 city 参数）",
                provider=provider.name,
                is_simulated=True,
            )
        try:
            snapshot = provider.fetch(query_city)
        except AppError as exc:
            return WeatherRead(available=False, reason=str(exc), provider=provider.name, is_simulated=True)
        return WeatherRead(
            available=True,
            reason=None,
            provider=provider.name,
            temperature_c=snapshot.temperature_c,
            humidity_pct=snapshot.humidity_pct,
            condition=snapshot.condition,
            city=snapshot.city,
            observed_at=snapshot.observed_at.isoformat(),
            is_simulated=snapshot.is_simulated,
        )

    def tips(self) -> WellbeingTips:
        rules = wellbeing_rules()
        return WellbeingTips(
            version=rules.version,
            source=rules.source,
            heat_levels=[HeatLevelRead(level=h.level, name=h.name, advice=h.advice) for h in rules.heat_levels],
            restriction=rules.restriction,
            special_groups=rules.special_groups,
            allowance=rules.allowance,
            tips=[WellbeingTipRead(id=t.id, text=t.text) for t in rules.tips],
            first_aid=[FirstAidStageRead(**vars(stage)) for stage in rules.first_aid],
            facilities=[FacilityRead(**vars(item)) for item in rules.facilities],
            load_error=rules.load_error,
        )

    # ---- 指标计算（确定性，代码注释文档化） ----

    @staticmethod
    def _risk_index(temperature_c: float, humidity_pct: float) -> int:
        """中暑风险指数 0~100：温度主导、湿度修正，确定性可复现。

        - 温度基分：<25℃→0；25~35℃→0~50；35~40℃→50~85；≥40℃→85~100；
        - 湿度修正：湿度>60% 时每超 4% 加 1 分（上限 +10）；湿度<40% 时每低 8% 减 1 分（下限 -5）。
        """
        if temperature_c < 25:
            base = 0.0
        elif temperature_c < 35:
            base = (temperature_c - 25) * 5
        elif temperature_c < 40:
            base = 50 + (temperature_c - 35) * 7
        else:
            base = 85 + (temperature_c - 40) * 3.75
        if humidity_pct > 60:
            adjustment = min((humidity_pct - 60) / 4.0, 10.0)
        elif humidity_pct < 40:
            adjustment = max((humidity_pct - 40) / 8.0, -5.0)
        else:
            adjustment = 0.0
        return round(max(0.0, min(100.0, base + adjustment)))

    @staticmethod
    def _risk_tier(risk_index: int) -> str:
        if risk_index < 30:
            return "低"
        if risk_index < 50:
            return "中"
        if risk_index < 75:
            return "高"
        return "极高"

    @staticmethod
    def _heat_index(temperature_c: float, humidity_pct: float) -> float:
        """体感温度（humidex 简化近似）：由温度/湿度估算露点后求 humidex。"""
        dew_point = temperature_c - (100.0 - humidity_pct) / 5.0
        vapor_pressure = 6.11 * math.exp(5417.7530 * (1 / 273.16 - 1 / (273.15 + dew_point)))
        return round(temperature_c + 0.5555 * (vapor_pressure - 10.0), 1)

    # ---- 响应组装 ----

    def _response(self, record: WellbeingRecord, rules: WellbeingRules) -> WellbeingAnalysisResponse:
        result = record.result_json if isinstance(record.result_json, dict) else {}
        return WellbeingAnalysisResponse(
            analysis_id=record.id,
            project_id=record.project_id,
            project_name=self._project_name(record.project_id),
            created_at=record.created_at.isoformat(),
            heat_level=record.heat_level,
            heat_level_name=str(result.get("heat_level_name", record.heat_level)),
            advice=str(result.get("advice", "")),
            restriction=str(result.get("restriction", "")),
            risk_index=record.risk_index or 0,
            risk_tier=str(result.get("risk_tier", self._risk_tier(record.risk_index or 0))),
            heat_index=record.heat_index,
            uv=str(result.get("uv", "中")),
            condition=str(result.get("condition", "")),
            temperature_c=float(result.get("temperature_c", 0.0)),
            humidity_pct=float(result.get("humidity_pct", 0.0)),
            description=str(result.get("description", "")),
            reminders=[WellbeingTipRead(**item) for item in result.get("reminders", [])],
            allowance=str(result.get("allowance", "")),
            special_groups=str(result.get("special_groups", "")),
            first_aid=[FirstAidStageRead(**item) for item in result.get("first_aid", [])],
            facilities=[FacilityRead(**item) for item in result.get("facilities", [])],
            broadcast=bool(result.get("broadcast", False)),
            is_simulated=record.is_simulated,
            source=str(result.get("source", rules.source)),
            rules_version=str(result.get("rules_version", rules.version)),
        )

    def _summary(self, record: WellbeingRecord) -> WellbeingRecordSummary:
        return WellbeingRecordSummary(
            analysis_id=record.id,
            project_id=record.project_id,
            project_name=self._project_name(record.project_id),
            heat_level=record.heat_level,
            risk_index=record.risk_index or 0,
            heat_index=record.heat_index,
            is_simulated=record.is_simulated,
            created_at=record.created_at.isoformat(),
        )

    def _project_name(self, project_id: str) -> str:
        project = self.db.get(Project, project_id)
        return project.name if project else project_id
