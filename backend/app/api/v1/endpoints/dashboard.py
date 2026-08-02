from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, ensure_project_access
from app.api.response import ok
from app.db.session import get_db
from app.models import Project, User
from app.services.dashboard_service import DashboardService


router = APIRouter(prefix="/dashboard", tags=["工作台"])


@router.get("/summary")
def summary(project_id: str, http_request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_project_access(project_id, user, db)
    return ok(DashboardService(db).summary(project_id, user), http_request)
