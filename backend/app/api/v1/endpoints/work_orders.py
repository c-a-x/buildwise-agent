from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.response import ok
from app.db.session import get_db
from app.models import User
from app.schemas.work_order import WorkOrderCreate, WorkOrderStatusUpdate
from app.services.work_order_service import WorkOrderService, work_order_dict


router = APIRouter(prefix="/work-orders", tags=["整改工单"])


@router.post("")
def create_order(request: WorkOrderCreate, http_request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = WorkOrderService(db)
    order = service.create(request, user)
    return ok(work_order_dict(order, service.events(order.id)), http_request, "工单已确认创建")


@router.get("")
def list_orders(http_request: Request, project_id: str | None = None, status: str | None = None, risk_level: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = WorkOrderService(db)
    orders = service.list(user, project_id=project_id, status=status, risk_level=risk_level)
    return ok([work_order_dict(order, service.events(order.id)) for order in orders], http_request)


@router.get("/{order_id}")
def get_order(order_id: str, http_request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = WorkOrderService(db)
    order = service.get(order_id, user)
    return ok(work_order_dict(order, service.events(order.id)), http_request)


@router.patch("/{order_id}/status")
def update_status(order_id: str, request: WorkOrderStatusUpdate, http_request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = WorkOrderService(db)
    order = service.update_status(order_id, request, user)
    return ok(work_order_dict(order, service.events(order.id)), http_request, "工单状态已更新")


@router.post("/{order_id}/attachments")
async def attach(order_id: str, http_request: Request, attachment: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = WorkOrderService(db)
    order = service.get(order_id, user)
    if not attachment.content_type or not attachment.content_type.startswith("image/"):
        from app.core.exceptions import AppError

        raise AppError("整改附件必须是图片", "UPLOAD_INVALID_TYPE", 400)
    content = await attachment.read()
    return ok({"work_order_id": order.id, "filename": attachment.filename, "size_bytes": len(content), "stored": False, "message": "MVP 已接收附件元数据，正式归档将在后续版本启用"}, http_request)
