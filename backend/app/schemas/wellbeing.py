from __future__ import annotations

from pydantic import BaseModel, Field


class WellbeingAnalyzeForm(BaseModel):
    """工友关怀分析表单：手动输入天气/环境数据，离线确定性计算。"""

    project_id: str
    temperature_c: float = Field(ge=-50, le=60)
    humidity_pct: float = Field(default=50.0, ge=0, le=100)
    condition: str = Field(default="晴", max_length=16)  # 晴/多云/阴/小雨/中雨/雷阵雨
    description: str = Field(default="", max_length=300)
    city: str | None = None  # 天气来源城市（实时天气联动时带入，作为记录溯源）


class CareCity(BaseModel):
    """工友关怀城市下拉项。"""

    id: str
    name: str


class WeatherSourceRead(BaseModel):
    """关怀分析所用天气来源（实时天气联动/定时关怀溯源）。"""

    city: str | None = None
    provider: str | None = None
    observed_at: str | None = None  # 观测/预报时间（ISO 或日期字符串）


class WellbeingTipRead(BaseModel):
    id: str
    text: str


class FirstAidStageRead(BaseModel):
    stage: str
    symptoms: str
    action: str


class FacilityRead(BaseModel):
    name: str
    location: str
    hours: str
    note: str


class HeatLevelRead(BaseModel):
    level: str  # none | yellow | orange | red
    name: str
    advice: str


class WellbeingAnalysisResponse(BaseModel):
    analysis_id: str
    project_id: str
    project_name: str
    created_at: str
    heat_level: str
    heat_level_name: str
    advice: str
    restriction: str
    risk_index: int  # 0~100
    risk_tier: str  # 低/中/高/极高
    heat_index: float | None  # 体感温度（humidex 近似）
    uv: str
    condition: str
    temperature_c: float
    humidity_pct: float
    description: str
    reminders: list[WellbeingTipRead]
    allowance: str
    special_groups: str
    first_aid: list[FirstAidStageRead]
    facilities: list[FacilityRead]
    broadcast: bool  # 是否已联动现场语音广播（达到档位且配置了 BROADCAST_WEBHOOK_URL）
    broadcast_eligible: bool = False  # 是否达到播报/蜂鸣器触发档位（不依赖 webhook 配置）
    buzzer: bool = False  # 是否已联动现场蜂鸣器硬报警（达到档位且配置了 ALERT_WEBHOOK_URL）
    is_simulated: bool
    source: str
    rules_version: str
    auto: bool = False  # 是否系统定时关怀自动生成（非手动）
    weather_source: WeatherSourceRead | None = None  # 天气来源（城市/Provider/时间）


class WellbeingRecordSummary(BaseModel):
    analysis_id: str
    project_id: str
    project_name: str
    heat_level: str
    risk_index: int
    heat_index: float | None
    is_simulated: bool
    created_at: str
    city: str | None = None  # 天气来源城市
    auto: bool = False  # 是否系统定时关怀自动生成


class WeatherRead(BaseModel):
    """实时天气查询结果：available=false 表示未配置/请求失败，前端回退手动输入。"""

    available: bool
    reason: str | None
    provider: str | None
    temperature_c: float | None = None
    humidity_pct: float | None = None
    condition: str | None = None
    city: str | None = None
    observed_at: str | None = None
    is_simulated: bool = False


class WellbeingTips(BaseModel):
    """工友关怀规则库静态内容（前端提示/急救/设施展示用）。"""

    version: str
    source: str
    heat_levels: list[HeatLevelRead]
    restriction: dict[str, str]
    special_groups: str
    allowance: str
    tips: list[WellbeingTipRead]
    first_aid: list[FirstAidStageRead]
    facilities: list[FacilityRead]
    load_error: str = ""
