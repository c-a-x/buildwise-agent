from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.dependencies import ensure_project_access, get_current_user
from app.api.response import ok
from app.db.session import get_db
from app.models import User
from app.services.stats_service import StatsService


router = APIRouter(prefix="/stats", tags=["统计"])


@router.get("/anomalies")
def anomalies(
    http_request: Request,
    project_id: str,
    module: str = Query("safety", pattern="^(safety|quality)$"),
    days: int = Query(30),
    z_threshold: float = Query(2.5),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_project_access(project_id, user, db)
    return ok(StatsService(db).anomaly_detection(project_id=project_id, module=module, days=days, z_threshold=z_threshold), http_request)
