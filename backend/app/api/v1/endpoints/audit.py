from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.api.response import ok
from app.db.session import get_db
from app.models import User
from app.schemas.audit import AuditLogListResponse, AuditLogRead
from app.services.audit_service import AuditService


router = APIRouter(prefix="/audit", tags=["权限审计"])


@router.get("/logs")
def list_logs(
    http_request: Request,
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
    user_id: str | None = Query(None, description="按操作人过滤"),
    action: str | None = Query(None, description="按动作过滤，如 user_login/confirm_work_order"),
    resource_type: str | None = Query(None, description="按资源类型过滤，如 auth/project/work_order"),
    start_at: datetime | None = Query(None),
    end_at: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """审计日志查询（仅管理员）：返回分页条目 + 总数，可按操作/用户/资源/时间过滤。"""
    items, total = AuditService(db).list(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        start_at=start_at,
        end_at=end_at,
        limit=limit,
        offset=offset,
    )
    payload = AuditLogListResponse(items=[AuditLogRead(**item) for item in items], total=total, limit=limit, offset=offset)
    return ok(payload.model_dump(), http_request)


@router.get("/actions")
def list_actions(http_request: Request, user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    """已出现的审计动作列表（仅管理员），供前端筛选下拉使用。"""
    return ok(AuditService(db).actions(), http_request)
