from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError
from app.models import DailyReport, Incident, ProjectMember, User, WorkOrder
from app.providers.text.template import TemplateTextProvider
from app.repositories.report_repository import ReportRepository
from app.utils.ids import new_id


class ReportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.reports = ReportRepository(db)
        self.provider = TemplateTextProvider()

    def generate(self, project_id: str, report_date: date, actor: User) -> DailyReport:
        if actor.role not in {"admin", "project_manager", "safety_officer"}:
            raise ForbiddenError("当前角色不能生成日报")
        if actor.role != "admin" and not self.db.query(ProjectMember).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == actor.id).first():
            raise ForbiddenError("无权访问该项目")
        start = datetime.combine(report_date, time.min, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        incident_query = self.db.query(Incident).filter(Incident.project_id == project_id, Incident.created_at >= start, Incident.created_at < end)
        incident_total = incident_query.count()
        risk_rows = self.db.query(Incident.risk_level, func.count(Incident.id)).filter(Incident.project_id == project_id, Incident.created_at >= start, Incident.created_at < end).group_by(Incident.risk_level).all()
        risk_counts = {str(level): int(count) for level, count in risk_rows}
        high_risk_total = sum(risk_counts.get(level, 0) for level in ("high", "critical"))
        order_query = self.db.query(WorkOrder).filter(WorkOrder.project_id == project_id)
        new_work_orders = order_query.filter(WorkOrder.created_at >= start, WorkOrder.created_at < end).count()
        closed_work_orders = order_query.filter(WorkOrder.closed_at >= start, WorkOrder.closed_at < end).count()
        status_rows = self.db.query(WorkOrder.status, func.count(WorkOrder.id)).filter(WorkOrder.project_id == project_id).group_by(WorkOrder.status).all()
        work_order_counts = {str(status): int(count) for status, count in status_rows}
        pending_review = work_order_counts.get("pending_review", 0)
        near_deadline = order_query.filter(WorkOrder.status != "closed", WorkOrder.deadline >= start, WorkOrder.deadline < end + timedelta(days=1)).count()
        hazard_rows = self.db.query(Incident.hazard_type, func.count(Incident.id)).filter(Incident.project_id == project_id, Incident.created_at >= start, Incident.created_at < end).group_by(Incident.hazard_type).order_by(func.count(Incident.id).desc()).limit(5).all()
        statistics = {
            "incident_total": incident_total,
            "risk_counts": risk_counts,
            "high_risk_total": high_risk_total,
            "work_order_counts": work_order_counts,
            "new_work_orders": new_work_orders,
            "closed_work_orders": closed_work_orders,
            "pending_review_work_orders": pending_review,
            "near_deadline_work_orders": near_deadline,
            "top_hazards": [{"hazard_type": str(kind), "count": int(count)} for kind, count in hazard_rows],
        }
        content = self.provider.generate_report({"statistics": statistics})
        report = self.reports.get_for_date(project_id, report_date)
        if report:
            report.statistics_json = statistics
            report.content = content
            report.generated_by = actor.id
            report.updated_at = datetime.now(timezone.utc)
        else:
            report = DailyReport(id=new_id("RPT"), project_id=project_id, report_date=report_date, statistics_json=statistics, content=content, generated_by=actor.id, is_ai_generated=False)
            self.db.add(report)
        self.db.commit()
        return report


def report_dict(report: DailyReport) -> dict[str, object]:
    return {
        "id": report.id,
        "project_id": report.project_id,
        "report_date": report.report_date,
        "statistics": report.statistics_json or {},
        "content": report.content,
        "generated_by": report.generated_by,
        "is_ai_generated": report.is_ai_generated,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
    }
