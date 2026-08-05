from __future__ import annotations

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
