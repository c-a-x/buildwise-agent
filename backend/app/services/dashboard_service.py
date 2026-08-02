from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError
from app.models import AgentRun, Incident, Project, ProjectMember, User, WorkOrder


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def summary(self, project_id: str, actor: User) -> dict[str, object]:
        if actor.role != "admin" and not self.db.query(ProjectMember).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == actor.id).first():
            project = self.db.get(Project, project_id)
            if not project or project.manager_user_id != actor.id:
                raise ForbiddenError("无权访问该项目")
        now = datetime.now(timezone.utc)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_incidents = self.db.query(Incident).filter(Incident.project_id == project_id, Incident.created_at >= today).count()
        high_risk = self.db.query(Incident).filter(Incident.project_id == project_id, Incident.risk_level.in_(["high", "critical"]), Incident.created_at >= today).count()
        pending = self.db.query(WorkOrder).filter(WorkOrder.project_id == project_id, WorkOrder.status.in_(["pending", "in_progress"])).count()
        pending_review = self.db.query(WorkOrder).filter(WorkOrder.project_id == project_id, WorkOrder.status == "pending_review").count()
        closed_total = self.db.query(WorkOrder).filter(WorkOrder.project_id == project_id, WorkOrder.status == "closed").count()
        total_orders = self.db.query(WorkOrder).filter(WorkOrder.project_id == project_id).count()
        risk_rows = self.db.query(Incident.risk_level, func.count(Incident.id)).filter(Incident.project_id == project_id).group_by(Incident.risk_level).all()
        status_rows = self.db.query(WorkOrder.status, func.count(WorkOrder.id)).filter(WorkOrder.project_id == project_id).group_by(WorkOrder.status).all()
        trend = []
        for offset in range(6, -1, -1):
            day = today - timedelta(days=offset)
            next_day = day + timedelta(days=1)
            trend.append({"date": day.date().isoformat(), "count": self.db.query(Incident).filter(Incident.project_id == project_id, Incident.created_at >= day, Incident.created_at < next_day).count()})
        recent_tasks = self.db.query(AgentRun).filter(AgentRun.project_id == project_id).order_by(AgentRun.created_at.desc()).limit(5).all()
        due_orders = self.db.query(WorkOrder).filter(WorkOrder.project_id == project_id, WorkOrder.status != "closed").order_by(WorkOrder.deadline.asc()).limit(5).all()
        member_count = self.db.query(ProjectMember).filter(ProjectMember.project_id == project_id).count()
        return {
            "metrics": {
                "today_incidents": today_incidents,
                "high_risk_incidents": high_risk,
                "pending_work_orders": pending,
                "pending_review_work_orders": pending_review,
                "weekly_close_rate": round(closed_total / total_orders * 100, 1) if total_orders else 0,
                "project_members": member_count,
            },
            "risk_distribution": [{"risk_level": str(level), "count": int(count)} for level, count in risk_rows],
            "work_order_distribution": [{"status": str(status), "count": int(count)} for status, count in status_rows],
            "risk_trend": trend,
            "recent_tasks": [{"task_id": item.id, "location": item.location, "risk_level": item.risk_level, "status": item.status, "created_at": item.created_at.isoformat()} for item in recent_tasks],
            "due_work_orders": [{"id": item.id, "title": item.title, "deadline": item.deadline.isoformat(), "risk_level": item.risk_level, "status": item.status} for item in due_orders],
        }
