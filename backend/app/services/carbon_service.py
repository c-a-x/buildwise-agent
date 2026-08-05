from __future__ import annotations

import statistics
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, NotFoundError
from app.models import CarbonAnalysis, Project
from app.providers.carbon import FactorLibrary, factor_library
from app.services.carbon_report import build_report_docx
from app.providers.carbon.factors import STAGE_NAMES
from app.schemas.green import (
    BenchmarkItem,
    CarbonAnalysisResponse,
    CarbonAnalysisSummary,
    CarbonContributor,
    CarbonItemRead,
    CarbonStageSummary,
    FactorRead,
    GreenAnalyzeForm,
    GreenBenchmark,
    GreenItemInput,
)
from app.utils.ids import new_id

UNIT = "tCO2e"


class CarbonService:
    """绿色碳排核算核心：GB/T 51366-2019 因子法 `排放 = Σ(活动数据 × 排放因子)`。

    Phase 1 不走五 Agent：直接计算 A1-A3（建材生产）/ A4（建材运输）/ A5（施工过程）
    分阶段排放，生成报告预览并持久化。绿色检测闭环留待 Phase 2。
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def analyze(
        self,
        *,
        project_id: str,
        area_m2: float | None,
        scope: str,
        materials: list[GreenItemInput],
        transport: list[GreenItemInput],
        energy: list[GreenItemInput],
        requested_by: str,
    ) -> CarbonAnalysisResponse:
        library = factor_library()
        warnings = [library.load_error] if library.load_error else []

        groups = (
            ("material", "A1-A3", materials),
            ("transport", "A4", transport),
            ("energy", "A5", energy),
        )
        items: list[CarbonItemRead] = []
        stage_emission = {"A1-A3": 0.0, "A4": 0.0, "A5": 0.0}
        stage_items: dict[str, int] = {"A1-A3": 0, "A4": 0, "A5": 0}
        used_factors: list[bool] = []

        for category, stage, inputs in groups:
            for entry in inputs:
                factor = library.get(entry.code) if entry.code else None
                factor_missing = factor is None
                emission = round(entry.quantity * factor.factor, 4) if factor else 0.0
                if factor_missing:
                    name = entry.name or entry.code or "未命名条目"
                    warnings.append(f"「{name}」未找到排放因子（code={entry.code or '未填写'}），已按 0 计。")
                items.append(
                    CarbonItemRead(
                        category=category,
                        stage=stage,
                        stage_name=STAGE_NAMES[stage],
                        code=entry.code,
                        name=entry.name or (factor.name if factor else entry.code),
                        unit=entry.unit or (factor.unit if factor else ""),
                        quantity=entry.quantity,
                        emission_factor=factor.factor if factor else None,
                        factor_unit=factor.factor_unit if factor else "tCO2e",
                        emission=emission,
                        factor_source=factor.source if factor else "",
                        verified=factor.verified if factor else False,
                        factor_missing=factor_missing,
                        note=entry.note,
                    )
                )
                stage_emission[stage] += emission
                stage_items[stage] += 1
                if factor:
                    used_factors.append(factor.verified)

        total = round(sum(stage_emission.values()), 4)
        intensity = round(total / area_m2, 4) if area_m2 and area_m2 > 0 else None
        has_unverified_factors = any(not verified for verified in used_factors)
        is_simulated = bool(warnings) or has_unverified_factors

        stages = [
            CarbonStageSummary(
                stage=stage,
                stage_name=STAGE_NAMES[stage],
                emission=round(stage_emission[stage], 4),
                share=round(stage_emission[stage] / total, 4) if total > 0 else 0.0,
                items_count=stage_items[stage],
            )
            for stage in ("A1-A3", "A4", "A5")
        ]
        contributors = self._top_contributors(items, total)
        suggestions = self._suggestions(stages, total)

        analysis = CarbonAnalysis(
            id=new_id("CAR"),
            project_id=project_id,
            requested_by=requested_by,
            area_m2=area_m2,
            scope=scope,
            total_emission=total,
            is_simulated=is_simulated,
            factor_version=library.version or "unavailable",
            result_json={
                "stages": [stage.model_dump() for stage in stages],
                "items": [item.model_dump() for item in items],
                "top_contributors": [contributor.model_dump() for contributor in contributors],
                "suggestions": suggestions,
                "factor_warnings": warnings,
                "has_unverified_factors": has_unverified_factors,
                "factor_version": library.version,
            },
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)

        report_preview = self._report_preview(project_id, analysis, stages, contributors, suggestions, warnings, library)
        analysis.report_preview = report_preview
        self.db.commit()
        self.db.refresh(analysis)

        return self._response(analysis, stages, items, contributors, suggestions, warnings, library)

    def list_analyses(self, project_id: str | None = None) -> list[CarbonAnalysisSummary]:
        query = self.db.query(CarbonAnalysis)
        if project_id:
            query = query.filter(CarbonAnalysis.project_id == project_id)
        analyses = query.order_by(CarbonAnalysis.created_at.desc()).all()
        return [self._summary(analysis) for analysis in analyses]

    def get_analysis(self, analysis_id: str) -> CarbonAnalysisResponse:
        analysis = self.db.get(CarbonAnalysis, analysis_id)
        if not analysis:
            raise NotFoundError("碳排分析不存在", "CARBON_ANALYSIS_NOT_FOUND")
        result = analysis.result_json if isinstance(analysis.result_json, dict) else {}
        stages = [CarbonStageSummary(**item) for item in result.get("stages", [])]
        items = [CarbonItemRead(**item) for item in result.get("items", [])]
        contributors = [CarbonContributor(**item) for item in result.get("top_contributors", [])]
        suggestions = result.get("suggestions", [])
        warnings = result.get("factor_warnings", [])
        library = factor_library()
        return CarbonAnalysisResponse(
            analysis_id=analysis.id,
            project_id=analysis.project_id,
            project_name=self._project_name(analysis.project_id),
            created_at=analysis.created_at.isoformat(),
            area_m2=analysis.area_m2,
            scope=analysis.scope,
            total_emission=analysis.total_emission or 0.0,
            unit=UNIT,
            intensity=round(analysis.total_emission / analysis.area_m2, 4) if analysis.area_m2 and analysis.area_m2 > 0 else None,
            stages=stages,
            items=items,
            top_contributors=contributors,
            suggestions=suggestions,
            factor_version=analysis.factor_version,
            has_unverified_factors=bool(result.get("has_unverified_factors", False)),
            factor_warnings=warnings,
            report_preview=analysis.report_preview,
            is_simulated=analysis.is_simulated,
        )

    def get_report(self, analysis_id: str) -> tuple[bytes, str, str, str]:
        """生成碳排报告 Word 字节流，返回 (body, filename, media_type, project_id)。"""
        analysis = self.db.get(CarbonAnalysis, analysis_id)
        if not analysis:
            raise NotFoundError("碳排分析不存在", "CARBON_ANALYSIS_NOT_FOUND")
        body, filename, media_type = build_report_docx(analysis, self._project_name(analysis.project_id))
        return body, filename, media_type, analysis.project_id

    def benchmark(self, project_ids: list[str], current_project_id: str | None = None) -> GreenBenchmark:
        """跨项目碳强度对标：每项目取最新一条有面积核算算 intensity，纯 Python z-score 排名。

        项目数 < 2 或强度标准差为 0 时降级为 `available=False` + 原因。
        """
        if not project_ids:
            return GreenBenchmark(
                available=False, reason="当前没有可见项目", count=0, mean=None, std=None, current=None, items=[]
            )
        analyses = (
            self.db.query(CarbonAnalysis)
            .filter(CarbonAnalysis.project_id.in_(project_ids), CarbonAnalysis.area_m2.isnot(None))
            .order_by(CarbonAnalysis.created_at.desc())
            .all()
        )
        latest_by_project: dict[str, CarbonAnalysis] = {}
        for analysis in analyses:
            if analysis.project_id not in latest_by_project:
                latest_by_project[analysis.project_id] = analysis

        rows: list[dict[str, object]] = []
        for analysis in latest_by_project.values():
            if not analysis.area_m2 or analysis.area_m2 <= 0 or not analysis.total_emission:
                continue
            intensity = analysis.total_emission / analysis.area_m2
            if intensity <= 0:
                continue
            rows.append(
                {
                    "project_id": analysis.project_id,
                    "project_name": self._project_name(analysis.project_id),
                    "intensity": round(intensity, 4),
                }
            )

        count = len(rows)
        if count < 2:
            return GreenBenchmark(
                available=False,
                reason=f"样本不足（{count} 个项目），至少需要 2 个项目",
                count=count,
                mean=None,
                std=None,
                current=None,
                items=[],
            )
        values = [float(row["intensity"]) for row in rows]
        mean = statistics.mean(values)
        std = statistics.stdev(values)
        if std == 0:
            return GreenBenchmark(
                available=False,
                reason="各项目面积强度一致，标准差为 0，无法对比",
                count=count,
                mean=round(mean, 4),
                std=0.0,
                current=None,
                items=[],
            )

        rows.sort(key=lambda row: float(row["intensity"]))
        items: list[BenchmarkItem] = []
        for index, row in enumerate(rows, start=1):
            intensity = float(row["intensity"])
            z = (intensity - mean) / std
            worse = sum(1 for other in rows if float(other["intensity"]) > intensity)
            items.append(
                BenchmarkItem(
                    rank=index,
                    project_id=str(row["project_id"]),
                    project_name=str(row["project_name"]),
                    intensity=intensity,
                    z=round(z, 3),
                    better_than_pct=round(100.0 * worse / count, 1),
                )
            )
        current = None
        if current_project_id:
            current = next((item for item in items if item.project_id == current_project_id), None)
        return GreenBenchmark(
            available=True,
            reason=None,
            count=count,
            mean=round(mean, 4),
            std=round(std, 4),
            current=current,
            items=items,
        )

    @staticmethod
    def _top_contributors(items: list[CarbonItemRead], total: float) -> list[CarbonContributor]:
        ranked = sorted(items, key=lambda item: item.emission, reverse=True)[:5]
        return [
            CarbonContributor(
                code=item.code,
                name=item.name,
                category=item.category,
                stage=item.stage,
                emission=item.emission,
                share=round(item.emission / total, 4) if total > 0 else 0.0,
            )
            for item in ranked
        ]

    @staticmethod
    def _suggestions(stages: list[CarbonStageSummary], total: float) -> list[str]:
        if total <= 0:
            return ["当前清单未命中有效排放因子，请补充因子库后重新核算。"]
        by_stage = {stage.stage: stage for stage in stages}
        a1 = by_stage["A1-A3"]
        a4 = by_stage["A4"]
        a5 = by_stage["A5"]
        suggestions: list[str] = []
        if a1.share >= 0.5:
            suggestions.append(f"建材生产阶段为主要排放来源（占比 {a1.share * 100:.0f}%），优先选用经第三方核证的绿色建材并优化结构设计、控制材料用量。")
        if a4.share >= 0.2:
            suggestions.append("建材运输阶段占比较高，优化运输线路与车辆调度，减少二次转运和空驶，优先使用新能源运输车辆。")
        if a5.share >= 0.2:
            suggestions.append("施工阶段占比较高，采用节能设备、错峰用电并加强临时用电管理，降低外购电力的间接排放。")
        suggestions.append("提高模板、脚手架等周转材料的使用次数，减少一次性材料消耗。")
        suggestions.append("绿色施工管理措施参照 GB/T 50905-2014 绿色施工方向落实，具体以项目绿色施工专项方案为准。")
        return suggestions

    def _report_preview(self, project_id: str, analysis: CarbonAnalysis, stages: list[CarbonStageSummary], contributors: list[CarbonContributor], suggestions: list[str], warnings: list[str], library: FactorLibrary) -> str:
        lines = [
            "# 绿色建造碳排核算报告",
            f"- 分析编号：{analysis.id}",
            f"- 项目：{self._project_name(project_id)}（{project_id}）",
            f"- 建筑面积：{analysis.area_m2} m²" if analysis.area_m2 else "- 建筑面积：未填写",
            f"- 核算范围：{analysis.scope or '施工阶段 A1-A3 / A4 / A5（GB/T 51366-2019 因子法）'}",
            f"- 因子库版本：{analysis.factor_version}",
            "",
            "## 核算结果",
            "| 阶段 | 排放（tCO2e） | 占比 |",
            "| --- | ---: | ---: |",
        ]
        for stage in stages:
            lines.append(f"| {stage.stage} {stage.stage_name} | {stage.emission} | {stage.share * 100:.1f}% |")
        lines.append("")
        lines.append(f"**总排放：{analysis.total_emission} tCO2e**")
        if analysis.area_m2:
            lines.append(f"**单位建筑面积排放：{analysis.total_emission / analysis.area_m2:.4f} tCO2e/m²**")
        lines.append("")
        lines.append("## 主要贡献项")
        lines.append("| 项目 | 阶段 | 排放（tCO2e） | 占比 |")
        lines.append("| --- | --- | ---: | ---: |")
        for contributor in contributors:
            lines.append(f"| {contributor.name} | {contributor.stage} | {contributor.emission} | {contributor.share * 100:.1f}% |")
        lines.append("")
        lines.append("## 减排建议")
        for index, suggestion in enumerate(suggestions, start=1):
            lines.append(f"{index}. {suggestion}")
        if warnings:
            lines.append("")
            lines.append("## 说明与核证提示")
            lines.append("以下因子未核证或缺失，结果仅供演示，正式核算需替换为经核证的因子数据：")
            for warning in warnings:
                lines.append(f"- {warning}")
        return "\n".join(lines)

    def _response(self, analysis: CarbonAnalysis, stages: list[CarbonStageSummary], items: list[CarbonItemRead], contributors: list[CarbonContributor], suggestions: list[str], warnings: list[str], library: FactorLibrary) -> CarbonAnalysisResponse:
        result = analysis.result_json if isinstance(analysis.result_json, dict) else {}
        return CarbonAnalysisResponse(
            analysis_id=analysis.id,
            project_id=analysis.project_id,
            project_name=self._project_name(analysis.project_id),
            created_at=analysis.created_at.isoformat(),
            area_m2=analysis.area_m2,
            scope=analysis.scope,
            total_emission=analysis.total_emission or 0.0,
            unit=UNIT,
            intensity=round(analysis.total_emission / analysis.area_m2, 4) if analysis.area_m2 and analysis.area_m2 > 0 else None,
            stages=stages,
            items=items,
            top_contributors=contributors,
            suggestions=suggestions,
            factor_version=analysis.factor_version,
            has_unverified_factors=bool(result.get("has_unverified_factors", False)),
            factor_warnings=warnings,
            report_preview=analysis.report_preview,
            is_simulated=analysis.is_simulated,
        )

    def _summary(self, analysis: CarbonAnalysis) -> CarbonAnalysisSummary:
        result = analysis.result_json if isinstance(analysis.result_json, dict) else {}
        return CarbonAnalysisSummary(
            analysis_id=analysis.id,
            project_id=analysis.project_id,
            project_name=self._project_name(analysis.project_id),
            area_m2=analysis.area_m2,
            scope=analysis.scope,
            total_emission=analysis.total_emission or 0.0,
            is_simulated=analysis.is_simulated,
            has_unverified_factors=bool(result.get("has_unverified_factors", False)),
            created_at=analysis.created_at.isoformat(),
        )

    def _project_name(self, project_id: str) -> str:
        project = self.db.get(Project, project_id)
        return project.name if project else project_id

    @staticmethod
    def factors() -> list[FactorRead]:
        library = factor_library()
        return [
            FactorRead(
                code=factor.code,
                category=factor.category,
                name=factor.name,
                unit=factor.unit,
                factor=factor.factor,
                factor_unit=factor.factor_unit,
                source=factor.source,
                year=factor.year,
                verified=factor.verified,
                note=factor.note,
            )
            for factor in library.factors
        ]
