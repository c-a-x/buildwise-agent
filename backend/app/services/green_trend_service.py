"""碳排趋势与目标：从 CarbonAnalysis 汇总面积强度历史曲线，项目强度目标 upsert。

grade 判定：intensity ≤ target 达标 / ≤ 1.1×target 临界 / 否则超标；未设目标返回「未设目标」。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import CarbonAnalysis, GreenTarget, Project
from app.schemas.green import GreenTargetForm, GreenTargetRead, GreenTrendCurrent, GreenTrendPoint, GreenTrendResponse
from app.utils.ids import new_id


class GreenTrendService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def trend(self, project_id: str) -> GreenTrendResponse:
        analyses = (
            self.db.query(CarbonAnalysis)
            .filter(CarbonAnalysis.project_id == project_id, CarbonAnalysis.area_m2.isnot(None), CarbonAnalysis.total_emission.isnot(None))
            .order_by(CarbonAnalysis.created_at.asc())
            .all()
        )
        points: list[GreenTrendPoint] = []
        for analysis in analyses:
            if not analysis.area_m2 or analysis.area_m2 <= 0 or not analysis.total_emission:
                continue
            points.append(
                GreenTrendPoint(
                    created_at=analysis.created_at.isoformat(),
                    total_emission=analysis.total_emission,
                    area_m2=analysis.area_m2,
                    intensity=round(analysis.total_emission / analysis.area_m2, 4),
                )
            )

        target = self.db.query(GreenTarget).filter(GreenTarget.project_id == project_id).one_or_none()
        target_intensity = target.target_intensity if target else None
        current_intensity = points[-1].intensity if points else None
        current = self._current(current_intensity, target_intensity)
        return GreenTrendResponse(project_id=project_id, project_name=self._project_name(project_id), points=points, current=current)

    def get_target(self, project_id: str) -> GreenTargetRead:
        target = self.db.query(GreenTarget).filter(GreenTarget.project_id == project_id).one_or_none()
        if target is None:
            return GreenTargetRead(project_id=project_id, target_intensity=None, note="", updated_at="")
        return GreenTargetRead(
            project_id=target.project_id,
            target_intensity=target.target_intensity,
            note=target.note,
            updated_at=target.updated_at.isoformat() if target.updated_at else "",
        )

    def set_target(self, form: GreenTargetForm, requested_by: str) -> GreenTargetRead:
        target = self.db.query(GreenTarget).filter(GreenTarget.project_id == form.project_id).one_or_none()
        if target is None:
            target = GreenTarget(id=new_id("TGT"), project_id=form.project_id, created_by=requested_by)
            self.db.add(target)
        target.target_intensity = form.target_intensity
        target.note = form.note
        self.db.commit()
        self.db.refresh(target)
        return GreenTargetRead(
            project_id=target.project_id,
            target_intensity=target.target_intensity,
            note=target.note,
            updated_at=target.updated_at.isoformat() if target.updated_at else "",
        )

    @staticmethod
    def _current(intensity: float | None, target_intensity: float | None) -> GreenTrendCurrent:
        if intensity is None:
            return GreenTrendCurrent(intensity=None, target_intensity=target_intensity, grade="未设目标" if target_intensity is None else "未核算", gap_pct=None)
        if target_intensity is None:
            return GreenTrendCurrent(intensity=intensity, target_intensity=None, grade="未设目标", gap_pct=None)
        gap_pct = round((intensity - target_intensity) / target_intensity * 100, 1) if target_intensity > 0 else None
        if intensity <= target_intensity:
            grade = "达标"
        elif intensity <= target_intensity * 1.1:
            grade = "临界"
        else:
            grade = "超标"
        return GreenTrendCurrent(intensity=intensity, target_intensity=target_intensity, grade=grade, gap_pct=gap_pct)

    def _project_name(self, project_id: str) -> str:
        project = self.db.get(Project, project_id)
        return project.name if project else project_id
