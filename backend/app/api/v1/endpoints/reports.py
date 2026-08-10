from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles, ensure_project_access
from app.api.response import ok
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models import DailyReport, User
from app.schemas.report import DailyReportGenerate
from app.services.report_service import ReportService, report_dict

_REPORT_ROLES = ("admin", "project_manager", "safety_officer", "quality_inspector")


router = APIRouter(prefix="/reports", tags=["日报"])


@router.post("/daily/generate")
def generate(request: DailyReportGenerate, http_request: Request, user: User = Depends(require_roles(*_REPORT_ROLES)), db: Session = Depends(get_db)):
    ensure_project_access(request.project_id, user, db)
    report = ReportService(db).generate(request.project_id, request.report_date, user)
    return ok(report_dict(report), http_request, "日报已生成")


@router.get("/daily")
def daily(http_request: Request, project_id: str, report_date: date = Query(...), user: User = Depends(require_roles(*_REPORT_ROLES)), db: Session = Depends(get_db)):
    ensure_project_access(project_id, user, db)
    report = ReportService(db).reports.get_for_date(project_id, report_date)
    if not report:
        raise NotFoundError("该日期尚未生成日报", "REPORT_NOT_FOUND")
    return ok(report_dict(report), http_request)


@router.get("")
def history(http_request: Request, project_id: str | None = None, user: User = Depends(require_roles(*_REPORT_ROLES)), db: Session = Depends(get_db)):
    query = db.query(DailyReport)
    if project_id:
        ensure_project_access(project_id, user, db)
        query = query.filter(DailyReport.project_id == project_id)
    reports = query.order_by(DailyReport.report_date.desc()).limit(50).all()
    return ok([report_dict(report) for report in reports], http_request)
