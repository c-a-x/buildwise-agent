"""开发库绿色建造模块示例数据：调用现有 service 播种，逐实体幂等（count==0 才写）。

种子内容（均回填历史 created_at，供演示）：
- PRJ-001 碳排核算 ×3（强度递减 0.090 → 0.075 → 0.063）
- PRJ-001 四节一环保评估 ×2（优良 / 优秀，全指标填满 → 非模拟）
- PRJ-001 环保监测台账 ×4（含 2 条超标）
- PRJ-001 碳排强度目标 0.08
- PRJ-002 / PRJ-003 各 1 条核算（供跨项目基准对标，量按公开建筑面积缩放，仅供演示）
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models import CarbonAnalysis, GreenAssessment, GreenEnvRecord, GreenTarget
from app.schemas.green import (
    DimensionInput,
    GreenAssessmentForm,
    GreenEnvRecordForm,
    GreenItemInput,
    GreenMetricInput,
    GreenTargetForm,
)
from app.services.carbon_service import CarbonService
from app.services.green_assessment_service import GreenAssessmentService
from app.services.green_env_service import GreenEnvService
from app.services.green_trend_service import GreenTrendService

REQUESTED_BY = "USR-001"  # 演示项目经理（seed_database 已创建）
AREA_M2 = 8500
TARGET_INTENSITY = 0.08


def _item(code: str, quantity: float, unit: str) -> GreenItemInput:
    return GreenItemInput(code=code, quantity=quantity, unit=unit)


def _metric(key: str, value: float) -> GreenMetricInput:
    return GreenMetricInput(key=key, value=value)


_ASSESSMENT_METRIC_KEYS: dict[str, list[str]] = {
    "material": ["recycled_material_pct", "template_reuse_times", "material_recycle_rate"],
    "water": ["non_traditional_water_pct", "water_saving_pct"],
    "energy": ["energy_saving_pct", "renewable_energy_pct"],
    "land": ["land_saving_pct", "greening_rate"],
    "env": ["env_compliance_pct", "sewage_treatment_pct"],
}

# 碳排核算：材料/运输/能耗因子编码复用前端 fillSample 已验证命中库的四个。
CARBON_ANALYSES = [
    {
        "created_at": datetime(2026, 7, 1, tzinfo=timezone.utc),
        "scope": "一期基础施工阶段",
        "materials": [_item("CONCRETE_C30", 1830, "m³")],
        "transport": [_item("TRUCK_46T_DIESEL", 110000, "t·km")],
        "energy": [_item("GRID_ELEC", 384000, "kWh")],
    },
    {
        "created_at": datetime(2026, 7, 20, tzinfo=timezone.utc),
        "scope": "一期主体结构施工阶段",
        "materials": [_item("CONCRETE_C30", 860, "m³"), _item("REBAR_HOT_ROLLED", 120, "t")],
        "transport": [_item("TRUCK_46T_DIESEL", 51600, "t·km")],
        "energy": [_item("GRID_ELEC", 180000, "kWh")],
    },
    {
        "created_at": datetime(2026, 8, 5, tzinfo=timezone.utc),
        "scope": "一期二次结构与装修阶段",
        "materials": [_item("CONCRETE_C30", 720, "m³"), _item("REBAR_HOT_ROLLED", 100, "t")],
        "transport": [_item("TRUCK_46T_DIESEL", 43400, "t·km")],
        "energy": [_item("GRID_ELEC", 151000, "kWh")],
    },
]

# 四节一环保评估：全指标填满 → is_simulated=False。分值对应 优良 / 优秀。
ASSESSMENTS = [
    {
        "title": "基础阶段绿色施工评估",
        "created_at": datetime(2026, 7, 15, tzinfo=timezone.utc),
        "values": {
            "recycled_material_pct": 22, "template_reuse_times": 5, "material_recycle_rate": 40,
            "non_traditional_water_pct": 21, "water_saving_pct": 11,
            "energy_saving_pct": 14, "renewable_energy_pct": 7,
            "land_saving_pct": 14, "greening_rate": 15,
            "env_compliance_pct": 85, "sewage_treatment_pct": 80,
        },
    },
    {
        "title": "主体结构阶段评估",
        "created_at": datetime(2026, 8, 1, tzinfo=timezone.utc),
        "values": {
            "recycled_material_pct": 28, "template_reuse_times": 6, "material_recycle_rate": 45,
            "non_traditional_water_pct": 27, "water_saving_pct": 13,
            "energy_saving_pct": 18, "renewable_energy_pct": 9,
            "land_saving_pct": 17, "greening_rate": 18,
            "env_compliance_pct": 95, "sewage_treatment_pct": 92,
        },
    },
]

# 环保台账：record 2 PM2.5/TSP 超标，record 4 夜间噪声超标。
ENV_RECORDS = [
    {
        "record_date": date(2026, 7, 8),
        "values": {"pm25": 45, "pm10": 82, "tsp": 180, "noise_day_db": 62, "noise_night_db": 48, "cod_mg": 52, "ss_mg": 30, "ph": 7.4, "solid_waste_t": 2.0},
    },
    {
        "record_date": date(2026, 7, 22),
        "values": {"pm25": 120, "pm10": 130, "tsp": 340, "noise_day_db": 68, "noise_night_db": 52, "cod_mg": 60, "ss_mg": 34, "ph": 7.1, "solid_waste_t": 2.4},
    },
    {
        "record_date": date(2026, 8, 2),
        "values": {"pm25": 50, "pm10": 88, "tsp": 190, "noise_day_db": 63, "noise_night_db": 50, "cod_mg": 48, "ss_mg": 28, "ph": 7.6, "solid_waste_t": 2.5},
    },
    {
        "record_date": date(2026, 8, 9),
        "values": {"pm25": 58, "pm10": 95, "tsp": 210, "noise_day_db": 66, "noise_night_db": 62, "cod_mg": 55, "ss_mg": 32, "ph": 7.3, "solid_waste_t": 2.2},
    },
]

# 基准对标：真实项目各 1 条核算（量按公开建筑面积缩放，仅供演示）。
BENCHMARK_ANALYSES = [
    {
        "project_id": "PRJ-002",
        "area_m2": 437000,
        "scope": "超高层主体结构施工阶段（演示）",
        "created_at": datetime(2018, 1, 1, tzinfo=timezone.utc),
        "materials": [_item("CONCRETE_C30", 40000, "m³"), _item("REBAR_HOT_ROLLED", 7500, "t")],
        "transport": [_item("TRUCK_46T_DIESEL", 2400000, "t·km")],
        "energy": [_item("GRID_ELEC", 8000000, "kWh")],
    },
    {
        "project_id": "PRJ-003",
        "area_m2": 460000,
        "scope": "超高层主体结构施工阶段（演示）",
        "created_at": datetime(2016, 1, 1, tzinfo=timezone.utc),
        "materials": [_item("CONCRETE_C30", 36000, "m³"), _item("REBAR_HOT_ROLLED", 6800, "t")],
        "transport": [_item("TRUCK_46T_DIESEL", 2100000, "t·km")],
        "energy": [_item("GRID_ELEC", 7200000, "kWh")],
    },
]


def _seed_carbon(db: Session) -> int:
    if db.query(CarbonAnalysis).filter(CarbonAnalysis.project_id == "PRJ-001").count() > 0:
        return 0
    service = CarbonService(db)
    created = 0
    for spec in CARBON_ANALYSES:
        response = service.analyze(
            project_id="PRJ-001",
            area_m2=AREA_M2,
            scope=spec["scope"],
            materials=spec["materials"],
            transport=spec["transport"],
            energy=spec["energy"],
            requested_by=REQUESTED_BY,
        )
        _backdate(db, CarbonAnalysis, response.analysis_id, spec["created_at"])
        created += 1
    for spec in BENCHMARK_ANALYSES:
        if db.query(CarbonAnalysis).filter(CarbonAnalysis.project_id == spec["project_id"]).count() > 0:
            continue
        response = service.analyze(
            project_id=spec["project_id"],
            area_m2=spec["area_m2"],
            scope=spec["scope"],
            materials=spec["materials"],
            transport=spec["transport"],
            energy=spec["energy"],
            requested_by=REQUESTED_BY,
        )
        _backdate(db, CarbonAnalysis, response.analysis_id, spec["created_at"])
        created += 1
    return created


def _seed_assessments(db: Session) -> int:
    if db.query(GreenAssessment).filter(GreenAssessment.project_id == "PRJ-001").count() > 0:
        return 0
    service = GreenAssessmentService(db)
    created = 0
    for spec in ASSESSMENTS:
        dimensions = [
            DimensionInput(dimension=dim_key, metrics=[_metric(key, spec["values"][key]) for key in keys])
            for dim_key, keys in _ASSESSMENT_METRIC_KEYS.items()
        ]
        form = GreenAssessmentForm(project_id="PRJ-001", title=spec["title"], area_m2=AREA_M2, dimensions=dimensions)
        response = service.evaluate(form, REQUESTED_BY)
        _backdate(db, GreenAssessment, response.assessment_id, spec["created_at"])
        created += 1
    return created


def _seed_env_records(db: Session) -> int:
    if db.query(GreenEnvRecord).filter(GreenEnvRecord.project_id == "PRJ-001").count() > 0:
        return 0
    service = GreenEnvService(db)
    created = 0
    for spec in ENV_RECORDS:
        form = GreenEnvRecordForm(project_id="PRJ-001", record_date=spec["record_date"], **spec["values"])
        response = service.upsert_record(form, REQUESTED_BY)
        _backdate(db, GreenEnvRecord, response.record_id, datetime.combine(spec["record_date"], datetime.min.time(), tzinfo=timezone.utc))
        created += 1
    return created


def _seed_target(db: Session) -> bool:
    if db.query(GreenTarget).filter(GreenTarget.project_id == "PRJ-001").count() > 0:
        return False
    form = GreenTargetForm(project_id="PRJ-001", target_intensity=TARGET_INTENSITY, note="对标行业先进水平（0.08 tCO2e/m²）")
    GreenTrendService(db).set_target(form, REQUESTED_BY)
    row = db.query(GreenTarget).filter(GreenTarget.project_id == "PRJ-001").one()
    row.created_at = datetime(2026, 7, 1, tzinfo=timezone.utc)
    row.updated_at = datetime(2026, 8, 1, tzinfo=timezone.utc)
    return True


def _backdate(db: Session, model, row_id: str, when: datetime) -> None:
    row = db.get(model, row_id)
    if row is not None:
        row.created_at = when


def seed_green_demo(db: Session) -> None:
    """播种绿色建造示例数据（幂等）。调用方需已完成基础 users/projects 提交。"""
    created_carbon = _seed_carbon(db)
    created_assessments = _seed_assessments(db)
    created_env = _seed_env_records(db)
    created_target = _seed_target(db)
    db.commit()
    print(
        f"Green seed: carbon={created_carbon} assessments={created_assessments} "
        f"env_records={created_env} target={'set' if created_target else 'skipped'}"
    )
