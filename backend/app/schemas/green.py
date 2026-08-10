from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class GreenItemInput(BaseModel):
    """单条活动数据：code 为因子库编码（可空，缺失时按 factor_missing 处理）。"""

    code: str = ""
    name: str = ""
    quantity: float = Field(gt=0)
    unit: str = ""
    note: str = ""


class GreenAnalyzeForm(BaseModel):
    project_id: str
    area_m2: float | None = Field(default=None, gt=0)
    scope: str = ""
    materials: list[GreenItemInput] = Field(default_factory=list)
    transport: list[GreenItemInput] = Field(default_factory=list)
    energy: list[GreenItemInput] = Field(default_factory=list)


class CarbonItemRead(BaseModel):
    category: str  # material | energy | transport
    stage: str  # A1-A3 | A4 | A5
    stage_name: str
    code: str
    name: str
    unit: str
    quantity: float
    emission_factor: float | None
    factor_unit: str
    emission: float  # tCO2e
    factor_source: str
    verified: bool = False
    factor_missing: bool = False
    note: str = ""


class CarbonStageSummary(BaseModel):
    stage: str
    stage_name: str
    emission: float
    share: float  # 0~1，占总量比例
    items_count: int


class CarbonContributor(BaseModel):
    code: str
    name: str
    category: str
    stage: str
    emission: float
    share: float


class CarbonAnalysisResponse(BaseModel):
    analysis_id: str
    project_id: str
    project_name: str
    created_at: str
    area_m2: float | None
    scope: str
    total_emission: float
    unit: str = "tCO2e"
    intensity: float | None  # tCO2e/m2
    stages: list[CarbonStageSummary]
    items: list[CarbonItemRead]
    top_contributors: list[CarbonContributor]
    suggestions: list[str]
    factor_version: str
    has_unverified_factors: bool
    factor_warnings: list[str]
    report_preview: str
    is_simulated: bool


class CarbonAnalysisSummary(BaseModel):
    analysis_id: str
    project_id: str
    project_name: str
    area_m2: float | None
    scope: str
    total_emission: float
    is_simulated: bool
    has_unverified_factors: bool
    created_at: str


class BenchmarkItem(BaseModel):
    """跨项目碳强度对标中的单个项目。"""

    rank: int
    project_id: str
    project_name: str
    intensity: float | None  # tCO2e/m²
    z: float  # (intensity-mean)/std，负值=低于均值=更优
    better_than_pct: float  # 0~100，池内严格劣于当前的项目占比


class GreenBenchmark(BaseModel):
    """按用户可见项目池，用最新一次核算的面积强度做 z-score 排名。"""

    available: bool
    reason: str | None  # 不可用原因，如「样本不足 2 个项目」/「标准差为 0」
    count: int
    metric: str = "intensity"
    unit: str = "tCO2e/m²"
    mean: float | None
    std: float | None
    current: BenchmarkItem | None  # 当前项目在榜内的位置
    items: list[BenchmarkItem]  # 按 intensity 升序，rank 1 最优


class FactorRead(BaseModel):
    code: str
    category: str
    name: str
    unit: str
    factor: float
    factor_unit: str
    source: str
    year: int | None = None
    verified: bool = False
    note: str = ""


class ReferenceMetricRead(BaseModel):
    """单条真实公开数据（如中国建筑 2024 年度 ESG/年报披露）。"""

    code: str
    name: str
    value: str
    unit: str
    year: int | None = None
    source: str
    note: str = ""


class ReferenceGroupRead(BaseModel):
    category: str
    name: str
    items: list[ReferenceMetricRead]


class GreenReference(BaseModel):
    """真实公开数据参考库（独立于本项目 z-score 对标，供对标参考）。"""

    version: str
    updated_at: str
    source_note: str
    groups: list[ReferenceGroupRead]


# ---------- 四节一环保评估 ----------


class GreenMetricInput(BaseModel):
    """单个评估指标输入。value 可空：缺失的指标该维度按 0 计并标记模拟。"""

    key: str
    value: float | None = Field(default=None, ge=0)


class DimensionInput(BaseModel):
    """一个维度的子指标输入。dimension 取值 material | water | energy | land | env。"""

    dimension: str
    metrics: list[GreenMetricInput] = Field(default_factory=list)


class GreenAssessmentForm(BaseModel):
    project_id: str
    title: str = ""
    area_m2: float | None = Field(default=None, ge=0)
    dimensions: list[DimensionInput] = Field(default_factory=list)


class MetricScore(BaseModel):
    key: str
    name: str
    value: float | None
    target: float
    direction: str  # higher | lower
    score: float  # 0~100


class DimensionScore(BaseModel):
    dimension: str
    name: str
    score: float  # 子指标得分均值 0~100
    metrics: list[MetricScore]


class GreenAssessmentResponse(BaseModel):
    assessment_id: str
    project_id: str
    project_name: str
    title: str
    area_m2: float | None
    total_score: float
    level: str  # 不合格 | 合格 | 优良 | 优秀
    dimensions: list[DimensionScore]
    is_simulated: bool
    report_preview: str
    created_at: str


class GreenAssessmentSummary(BaseModel):
    assessment_id: str
    project_id: str
    project_name: str
    title: str
    total_score: float
    level: str
    is_simulated: bool
    created_at: str


# ---------- 环保监测台账 ----------


class GreenEnvRecordForm(BaseModel):
    """当日环保监测读数，均可空。同一项目+日期重复提交为 upsert（幂等重录）。"""

    project_id: str
    record_date: date
    pm25: float | None = Field(default=None, ge=0)
    pm10: float | None = Field(default=None, ge=0)
    tsp: float | None = Field(default=None, ge=0)
    noise_day_db: float | None = Field(default=None, ge=0)
    noise_night_db: float | None = Field(default=None, ge=0)
    cod_mg: float | None = Field(default=None, ge=0)
    ss_mg: float | None = Field(default=None, ge=0)
    ph: float | None = Field(default=None, ge=0)
    solid_waste_t: float | None = Field(default=None, ge=0)


class EnvThresholdRead(BaseModel):
    """UI 展示用阈值常量。rule=above 超上限告警；rule=range 越界告警（如 pH）。"""

    key: str
    name: str
    unit: str
    rule: str  # above | range
    limit: float | None = None
    min: float | None = None
    max: float | None = None


class EnvAlertRead(BaseModel):
    key: str
    name: str
    value: float
    rule: str
    limit: float | None = None
    min: float | None = None
    max: float | None = None


class EnvRecordRead(BaseModel):
    record_id: str
    project_id: str
    project_name: str
    record_date: str
    pm25: float | None
    pm10: float | None
    tsp: float | None
    noise_day_db: float | None
    noise_night_db: float | None
    cod_mg: float | None
    ss_mg: float | None
    ph: float | None
    solid_waste_t: float | None
    has_alerts: bool
    alerts: list[EnvAlertRead]
    created_at: str


# ---------- 碳排趋势与目标 ----------


class GreenTargetForm(BaseModel):
    project_id: str
    target_intensity: float | None = Field(default=None, gt=0)
    note: str = ""


class GreenTargetRead(BaseModel):
    project_id: str
    target_intensity: float | None
    note: str
    updated_at: str


class GreenTrendPoint(BaseModel):
    created_at: str
    total_emission: float
    area_m2: float
    intensity: float


class GreenTrendCurrent(BaseModel):
    intensity: float | None
    target_intensity: float | None
    grade: str  # 达标 | 临界 | 超标 | 未设目标
    gap_pct: float | None  # 相对目标百分比，负值=优于目标


class GreenTrendResponse(BaseModel):
    project_id: str
    project_name: str
    points: list[GreenTrendPoint]
    current: GreenTrendCurrent


# ---------- AI 优化建议 ----------


class GreenAdviceForm(BaseModel):
    project_id: str
    source_type: str  # carbon | assessment
    analysis_id: str | None = None
    assessment_id: str | None = None


class GreenAdviceRead(BaseModel):
    advice: str
    is_simulated: bool
    source_type: str
    generated_at: str
