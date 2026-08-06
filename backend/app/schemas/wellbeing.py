from __future__ import annotations

from pydantic import BaseModel, Field


class WellbeingAnalyzeForm(BaseModel):
    """工友关怀分析表单：手动输入天气/环境数据，离线确定性计算。"""

    project_id: str
    temperature_c: float = Field(ge=-50, le=60)
    humidity_pct: float = Field(default=50.0, ge=0, le=100)
    condition: str = Field(default="晴", max_length=16)  # 晴/多云/阴/小雨/中雨/雷阵雨
    description: str = Field(default="", max_length=300)


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
    broadcast: bool  # 是否已联动现场语音广播（红色高温且配置了 webhook）
    is_simulated: bool
    source: str
    rules_version: str


class WellbeingRecordSummary(BaseModel):
    analysis_id: str
    project_id: str
    project_name: str
    heat_level: str
    risk_index: int
    heat_index: float | None
    is_simulated: bool
    created_at: str


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
