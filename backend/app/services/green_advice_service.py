"""AI 绿色施工优化建议：基于碳排核算或四节一环保评估，由 DeepSeek 生成 3~6 条行动建议。

- LLM 可用（openai_compatible + 三件套）且调用成功 → is_simulated 跟随源数据（演示数据为 True）。
- LLM 未配置或失败 → 降级静态建议：碳排复用 CarbonService._suggestions，评估用低分维度预置建议，is_simulated=True。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import Settings, settings as default_settings
from app.core.exceptions import NotFoundError
from app.models import CarbonAnalysis, GreenAssessment, Project
from app.providers.factory import build_text_provider
from app.schemas.green import CarbonStageSummary, GreenAdviceForm, GreenAdviceRead

DIMENSION_TIPS = {
    "material": "节材维度得分偏低：优先采用可循环材料与高周转模板，提高建筑垃圾回收利用率，减少一次性材料投入。",
    "water": "节水维度得分偏低：推广非传统水源（雨水收集、中水回用）用于降尘与绿化，加强施工用水计量与定额管理。",
    "energy": "节能维度得分偏低：优先选用节能型施工机械并错峰用电，提升可再生能源（如太阳能）在临时用电中的占比。",
    "land": "节地维度得分偏低：优化施工总平面布置、压缩临时占地，提升现场绿化率，落实节约集约用地要求。",
    "env": "环境保护维度得分偏低：严格落实扬尘、噪声、污水与固废管控措施，确保环保设施运行率和达标排放。",
}


class GreenAdviceService:
    def __init__(self, db: Session, runtime_settings: Settings | None = None) -> None:
        self.db = db
        self.settings = runtime_settings or default_settings

    def generate(self, form: GreenAdviceForm) -> GreenAdviceRead:
        payload = self._build_payload(form)
        if self._llm_ready():
            try:
                text_provider = build_text_provider(self.settings)
                advice = str(text_provider.generate_green_advice(payload)).strip()
                if advice:
                    return GreenAdviceRead(advice=advice, is_simulated=bool(payload.get("is_demo", False)), source_type=form.source_type, generated_at=datetime.now(timezone.utc).isoformat())
            except Exception:
                pass  # LLM 调用失败不阻断，降级静态建议
        return GreenAdviceRead(advice=self._fallback(payload), is_simulated=True, source_type=form.source_type, generated_at=datetime.now(timezone.utc).isoformat())

    def _llm_ready(self) -> bool:
        return (
            self.settings.text_provider == "openai_compatible"
            and bool(self.settings.llm_base_url)
            and bool(self.settings.llm_api_key)
            and bool(self.settings.llm_model)
        )

    def _build_payload(self, form: GreenAdviceForm) -> dict[str, object]:
        payload: dict[str, object] = {"source_type": form.source_type, "project_id": form.project_id, "project_name": self._project_name(form.project_id)}
        if form.source_type == "carbon":
            analysis = self._resolve_analysis(form)
            if analysis is not None:
                result = analysis.result_json if isinstance(analysis.result_json, dict) else {}
                payload.update(
                    {
                        "total_emission": analysis.total_emission or 0.0,
                        "intensity": round(analysis.total_emission / analysis.area_m2, 4) if analysis.area_m2 and analysis.area_m2 > 0 else None,
                        "stage_shares": {item.get("stage"): item.get("share", 0) for item in result.get("stages", [])},
                        "current_suggestions": result.get("suggestions", []),
                        "is_demo": analysis.is_simulated,
                    }
                )
        else:
            assessment = self._resolve_assessment(form)
            if assessment is not None:
                result = assessment.result_json if isinstance(assessment.result_json, dict) else {}
                dimensions = result.get("dimensions", [])
                payload.update(
                    {
                        "total_score": assessment.total_score or 0.0,
                        "level": assessment.level or "",
                        "low_dimensions": [item for item in dimensions if (item.get("score") if isinstance(item, dict) else 0) < 70],
                        "is_demo": assessment.is_simulated,
                    }
                )
        return payload

    def _resolve_analysis(self, form: GreenAdviceForm) -> CarbonAnalysis | None:
        if form.analysis_id:
            analysis = self.db.get(CarbonAnalysis, form.analysis_id)
            if not analysis:
                raise NotFoundError("碳排分析不存在", "CARBON_ANALYSIS_NOT_FOUND")
            return analysis
        return (
            self.db.query(CarbonAnalysis)
            .filter(CarbonAnalysis.project_id == form.project_id, CarbonAnalysis.total_emission.isnot(None))
            .order_by(CarbonAnalysis.created_at.desc())
            .first()
        )

    def _resolve_assessment(self, form: GreenAdviceForm) -> GreenAssessment | None:
        if form.assessment_id:
            assessment = self.db.get(GreenAssessment, form.assessment_id)
            if not assessment:
                raise NotFoundError("四节一环保评估不存在", "GREEN_ASSESSMENT_NOT_FOUND")
            return assessment
        return self.db.query(GreenAssessment).filter(GreenAssessment.project_id == form.project_id).order_by(GreenAssessment.created_at.desc()).first()

    def _fallback(self, payload: dict[str, object]) -> str:
        if str(payload.get("source_type", "carbon")) == "assessment":
            low = payload.get("low_dimensions", [])
            tips = []
            for item in (low if isinstance(low, list) else [])[:3]:
                dimension = item.get("dimension", "") if isinstance(item, dict) else ""
                if dimension in DIMENSION_TIPS:
                    tips.append(DIMENSION_TIPS[dimension])
            if not tips:
                tips = ["各维度均达到合格线，建议持续保持并定期复盘绿色施工专项方案落实情况。"]
            return "\n".join(f"{index}. {tip}" for index, tip in enumerate(tips, start=1))

        stages = []
        for stage, share in (payload.get("stage_shares", {}) or {}).items():
            stages.append(
                CarbonStageSummary(stage=stage, stage_name="", emission=0.0, share=float(share or 0), items_count=0)
            )
        from app.services.carbon_service import CarbonService

        suggestions = CarbonService._suggestions(stages, float(payload.get("total_emission", 0) or 0))
        return "\n".join(f"{index}. {suggestion}" for index, suggestion in enumerate(suggestions, start=1))

    def _project_name(self, project_id: str) -> str:
        project = self.db.get(Project, project_id)
        return project.name if project else project_id
