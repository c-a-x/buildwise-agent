from __future__ import annotations

import math
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import Settings, settings as default_settings
from app.core.exceptions import AppError, NotFoundError
from app.models import Project, WellbeingRecord
from app.providers.factory import build_weather_provider
from app.providers.wellbeing import WellbeingRules, wellbeing_rules
from app.providers.weather.qweather import CITY_NAMES, _CITY_LOCATION_IDS
from app.schemas.wellbeing import (
    CareCity,
    FacilityRead,
    FirstAidStageRead,
    HeatLevelRead,
    WellbeingAnalysisResponse,
    WellbeingRecordSummary,
    WellbeingTips,
    WellbeingTipRead,
    WeatherRead,
    WeatherSourceRead,
)
from app.utils.ids import new_id

# 广播触发档位：red=仅红色高温；orange=橙/红色高温（定时关怀按预报日最高气温时用橙档更早预警）
_BROADCAST_LEVEL_ORDER = {"none": 0, "yellow": 1, "orange": 2, "red": 3}

_BROADCAST_MESSAGES = {
    "red": "高温红色预警！当前气温{}℃，已达当日最高气温40℃以上，应当立即停止当日室外露天作业，转移到阴凉处休息，注意多喝淡盐水。",
    "orange": "高温橙色预警！当前气温{}℃，已达当日最高气温37℃以上，全天室外露天作业累计不超过6小时，气温最高时段3小时内不得安排室外露天作业，请做好防暑降温。",
}


def broadcast_message(data: WellbeingAnalysisResponse) -> str:
    """关怀播报文案（按高温等级）：端点与定时调度器共用。非红色/橙色高温返回空串。"""
    template = _BROADCAST_MESSAGES.get(data.heat_level)
    return template.format(round(data.temperature_c)) if template else ""


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
        requested_by: str | None = None,
        auto: bool = False,
        broadcast_threshold: str = "red",
        weather_source: WeatherSourceRead | None = None,
    ) -> WellbeingAnalysisResponse:
        rules = wellbeing_rules()
        is_simulated = bool(rules.load_error)

        heat_level = rules.heat_level_for(temperature_c)
        risk_index = self._risk_index(temperature_c, humidity_pct)
        heat_index = self._heat_index(temperature_c, humidity_pct)
        uv = rules.condition_uv.get(condition.strip() or "晴", "中")
        restriction = rules.restriction.get(heat_level.level, "")
        broadcast_eligible = _BROADCAST_LEVEL_ORDER.get(heat_level.level, 0) >= _BROADCAST_LEVEL_ORDER.get(broadcast_threshold, 3)
        broadcast = broadcast_eligible and bool(self.settings.broadcast_webhook_url)

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
                "broadcast_eligible": broadcast_eligible,
                "source": rules.source,
                "rules_version": rules.version,
                "auto": auto,
                "weather_source": weather_source.model_dump() if weather_source else None,
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

    def cities(self) -> list[CareCity]:
        """城市下拉候选：内置中文城市；配置的 WEATHER_CITY 用对应中文名展示（值保留配置别名），避免中英文重复。"""
        configured = self.settings.weather_city.strip()
        configured_id = _CITY_LOCATION_IDS.get(configured.lower()) if configured else None
        items: list[CareCity] = []
        for zh in CITY_NAMES:
            location_id = _CITY_LOCATION_IDS.get(zh)
            if configured_id and location_id == configured_id:
                # 配置城市：值用配置别名（beijing），展示中文名（北京），保证默认城市能匹配 weather.city
                items.append(CareCity(id=configured, name=zh))
            else:
                items.append(CareCity(id=zh, name=zh))
        return items

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
            broadcast_eligible=bool(result.get("broadcast_eligible", False)),
            buzzer=bool(result.get("buzzer", False)),
            is_simulated=record.is_simulated,
            source=str(result.get("source", rules.source)),
            rules_version=str(result.get("rules_version", rules.version)),
            auto=bool(result.get("auto", False)),
            weather_source=WeatherSourceRead(**result["weather_source"])
            if isinstance(result.get("weather_source"), dict)
            else None,
        )

    def _summary(self, record: WellbeingRecord) -> WellbeingRecordSummary:
        result = record.result_json if isinstance(record.result_json, dict) else {}
        weather_source = result.get("weather_source")
        return WellbeingRecordSummary(
            analysis_id=record.id,
            project_id=record.project_id,
            project_name=self._project_name(record.project_id),
            heat_level=record.heat_level,
            risk_index=record.risk_index or 0,
            heat_index=record.heat_index,
            is_simulated=record.is_simulated,
            created_at=record.created_at.isoformat(),
            city=str(weather_source["city"]) if isinstance(weather_source, dict) and weather_source.get("city") else None,
            auto=bool(result.get("auto", False)),
        )

    def _project_name(self, project_id: str) -> str:
        project = self.db.get(Project, project_id)
        return project.name if project else project_id
