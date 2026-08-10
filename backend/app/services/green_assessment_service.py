"""四节一环保评估：节材/节水/节能/节地/环境保护 五维打分 + 等级 + 报告预览。

评分规则：
- 每维度 = 其子指标得分均值（各 0~100）。
- 子指标越高越好：score = clamp(100 × value / target)；越低越好：score = clamp(100 × target / value)，value=0 → 100。
- 缺失输入 → 该指标按 0 计，触发 is_simulated（同碳排 factor-missing 语义）。
- total = round(Σ 维度 × 0.20, 1)；等级 ≥85 优秀 / ≥70 优良 / ≥60 合格 / 否则不合格。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models import GreenAssessment, Project
from app.schemas.green import DimensionScore, GreenAssessmentForm, GreenAssessmentResponse, GreenAssessmentSummary, GreenMetricInput, MetricScore
from app.services.green_assessment_report import build_assessment_docx
from app.utils.ids import new_id


# 维度定义：指标 key → 展示名 / 目标值 / 方向。direction=lower 时越低越好（取反）。
DIMENSIONS: dict[str, dict[str, object]] = {
    "material": {
        "name": "节材",
        "metrics": {
            "recycled_material_pct": {"name": "可循环材料利用率（%）", "target": 30, "direction": "higher"},
            "template_reuse_times": {"name": "模板周转次数（次）", "target": 6, "direction": "higher"},
            "material_recycle_rate": {"name": "建筑垃圾回收利用率（%）", "target": 50, "direction": "higher"},
        },
    },
    "water": {
        "name": "节水",
        "metrics": {
            "non_traditional_water_pct": {"name": "非传统水源利用率（%）", "target": 30, "direction": "higher"},
            "water_saving_pct": {"name": "节水节水量占比（%）", "target": 15, "direction": "higher"},
        },
    },
    "energy": {
        "name": "节能",
        "metrics": {
            "energy_saving_pct": {"name": "节能设备节电率（%）", "target": 20, "direction": "higher"},
            "renewable_energy_pct": {"name": "可再生能源占比（%）", "target": 10, "direction": "higher"},
        },
    },
    "land": {
        "name": "节地",
        "metrics": {
            "land_saving_pct": {"name": "节约集约用地率（%）", "target": 20, "direction": "higher"},
            "greening_rate": {"name": "现场绿化率（%）", "target": 20, "direction": "higher"},
        },
    },
    "env": {
        "name": "环境保护",
        "metrics": {
            "env_compliance_pct": {"name": "环保措施落实率（%）", "target": 100, "direction": "higher"},
            "sewage_treatment_pct": {"name": "污水达标处理率（%）", "target": 100, "direction": "higher"},
        },
    },
}

DIMENSION_WEIGHT = 0.20


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def score_metric(value: float | None, target: float, direction: str = "higher") -> float:
    """单指标得分 0~100。缺失输入 → 0。越低越好时按 target/value 取反。"""
    if value is None or target <= 0:
        return 0.0
    if direction == "lower":
        return _clamp(100.0 * target / value) if value > 0 else 100.0
    return _clamp(100.0 * value / target)


def level_for(score: float) -> str:
    if score >= 85:
        return "优秀"
    if score >= 70:
        return "优良"
    if score >= 60:
        return "合格"
    return "不合格"


def score_dimension(dimension: str, inputs: dict[str, float | None]) -> tuple[float, list[MetricScore], bool]:
    """单维度打分，返回 (维度均分, 指标得分列表, 是否有缺失指标)。"""
    config = DIMENSIONS[dimension]
    metric_scores: list[MetricScore] = []
    missing = False
    for key, metric in config["metrics"].items():  # type: ignore[attr-defined]
        value = inputs.get(key)
        score = score_metric(value, metric["target"], metric["direction"])  # type: ignore[attr-defined]
        if value is None:
            missing = True
        metric_scores.append(
            MetricScore(key=key, name=metric["name"], value=value, target=metric["target"], direction=metric["direction"], score=round(score, 1))  # type: ignore[attr-defined]
        )
    average = sum(item.score for item in metric_scores) / len(metric_scores) if metric_scores else 0.0
    return round(average, 1), metric_scores, missing


class GreenAssessmentService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def evaluate(self, form: GreenAssessmentForm, requested_by: str) -> GreenAssessmentResponse:
        dimension_scores: list[DimensionScore] = []
        any_missing = False
        for dimension in ("material", "water", "energy", "land", "env"):
            inputs = {metric.key: metric.value for metric in next((d.metrics for d in form.dimensions if d.dimension == dimension), [])}
            score, metric_scores, missing = score_dimension(dimension, inputs)
            any_missing = any_missing or missing
            dimension_scores.append(DimensionScore(dimension=dimension, name=DIMENSIONS[dimension]["name"], score=score, metrics=metric_scores))  # type: ignore[arg-type]

        total = round(sum(item.score for item in dimension_scores) * DIMENSION_WEIGHT, 1)
        level = level_for(total)
        is_simulated = any_missing

        assessment = GreenAssessment(
            id=new_id("GAS"),
            project_id=form.project_id,
            requested_by=requested_by,
            title=form.title,
            area_m2=form.area_m2,
            total_score=total,
            level=level,
            is_simulated=is_simulated,
            report_preview="",
            result_json={
                "dimensions": [item.model_dump() for item in dimension_scores],
                "total_score": total,
                "level": level,
            },
        )
        self.db.add(assessment)
        self.db.commit()
        self.db.refresh(assessment)

        report_preview = self._report_preview(form.project_id, assessment, dimension_scores, total, level)
        assessment.report_preview = report_preview
        self.db.commit()
        self.db.refresh(assessment)

        return GreenAssessmentResponse(
            assessment_id=assessment.id,
            project_id=assessment.project_id,
            project_name=self._project_name(form.project_id),
            title=assessment.title,
            area_m2=assessment.area_m2,
            total_score=total,
            level=level,
            dimensions=dimension_scores,
            is_simulated=is_simulated,
            report_preview=report_preview,
            created_at=assessment.created_at.isoformat(),
        )

    def list_assessments(self, project_id: str | None = None) -> list[GreenAssessmentSummary]:
        query = self.db.query(GreenAssessment)
        if project_id:
            query = query.filter(GreenAssessment.project_id == project_id)
        rows = query.order_by(GreenAssessment.created_at.desc()).all()
        return [self._summary(row) for row in rows]

    def get_assessment(self, assessment_id: str) -> GreenAssessmentResponse:
        assessment = self.db.get(GreenAssessment, assessment_id)
        if not assessment:
            raise NotFoundError("四节一环保评估不存在", "GREEN_ASSESSMENT_NOT_FOUND")
        result = assessment.result_json if isinstance(assessment.result_json, dict) else {}
        dimension_scores = [DimensionScore(**item) for item in result.get("dimensions", [])]
        return GreenAssessmentResponse(
            assessment_id=assessment.id,
            project_id=assessment.project_id,
            project_name=self._project_name(assessment.project_id),
            title=assessment.title,
            area_m2=assessment.area_m2,
            total_score=assessment.total_score or 0.0,
            level=assessment.level or level_for(assessment.total_score or 0.0),
            dimensions=dimension_scores,
            is_simulated=assessment.is_simulated,
            report_preview=assessment.report_preview,
            created_at=assessment.created_at.isoformat(),
        )

    def get_report(self, assessment_id: str) -> tuple[bytes, str, str, str]:
        assessment = self.db.get(GreenAssessment, assessment_id)
        if not assessment:
            raise NotFoundError("四节一环保评估不存在", "GREEN_ASSESSMENT_NOT_FOUND")
        body, filename, media_type = build_assessment_docx(assessment, self._project_name(assessment.project_id))
        return body, filename, media_type, assessment.project_id

    def _report_preview(self, project_id: str, assessment: GreenAssessment, dimension_scores: list[DimensionScore], total: float, level: str) -> str:
        lines = [
            "# 四节一环保评估报告",
            f"- 评估编号：{assessment.id}",
            f"- 项目：{self._project_name(project_id)}（{project_id}）",
            f"- 建筑面积：{assessment.area_m2} m²" if assessment.area_m2 else "- 建筑面积：未填写",
            "",
            f"**总分：{total}　等级：{level}**",
            "",
            "| 维度 | 得分 | 指标明细 |",
            "| --- | ---: | --- |",
        ]
        for item in dimension_scores:
            details = "；".join(f"{metric.name} {metric.score:.0f}" for metric in item.metrics)
            lines.append(f"| {item.name} | {item.score} | {details} |")
        if assessment.is_simulated:
            lines.append("")
            lines.append("> 部分指标未填写，按 0 分计，结果仅供演示，请补充完整数据后重新评估。")
        return "\n".join(lines)

    def _summary(self, assessment: GreenAssessment) -> GreenAssessmentSummary:
        return GreenAssessmentSummary(
            assessment_id=assessment.id,
            project_id=assessment.project_id,
            project_name=self._project_name(assessment.project_id),
            title=assessment.title,
            total_score=assessment.total_score or 0.0,
            level=assessment.level or level_for(assessment.total_score or 0.0),
            is_simulated=assessment.is_simulated,
            created_at=assessment.created_at.isoformat(),
        )

    def _project_name(self, project_id: str) -> str:
        project = self.db.get(Project, project_id)
        return project.name if project else project_id
