from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.response import ok
from app.core.config import settings
from app.db.session import get_db
from app.models import AuditLog, Upload, User, WorkOrderEvent
from app.schemas.work_order import WorkOrderCreate, WorkOrderStatusUpdate
from app.services.work_order_service import WorkOrderService
from app.utils.files import save_upload
from app.utils.ids import new_id


router = APIRouter(prefix="/work-orders", tags=["整改工单"])


@router.post("")
def create_order(request: WorkOrderCreate, http_request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = WorkOrderService(db)
    order = service.create(request, user)
    return ok(service.serialize(order), http_request, "工单已确认创建")


@router.get("")
def list_orders(
    http_request: Request,
    project_id: str | None = None,
    status: str | None = None,
    risk_level: str | None = None,
    assignee_user_id: str | None = None,
    deadline_from: datetime | None = None,
    deadline_to: datetime | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkOrderService(db)
    orders = service.list(user, project_id=project_id, status=status, risk_level=risk_level, assignee_user_id=assignee_user_id, deadline_from=deadline_from, deadline_to=deadline_to)
    return ok([service.serialize(order) for order in orders], http_request)


@router.get("/{order_id}")
def get_order(order_id: str, http_request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = WorkOrderService(db)
    order = service.get(order_id, user)
    return ok(service.serialize(order), http_request)


@router.patch("/{order_id}/status")
def update_status(order_id: str, request: WorkOrderStatusUpdate, http_request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = WorkOrderService(db)
    order = service.update_status(order_id, request, user)
    return ok(service.serialize(order), http_request, "工单状态已更新")


@router.post("/{order_id}/attachments")
async def attach(order_id: str, http_request: Request, attachment: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = WorkOrderService(db)
    order = service.get(order_id, user)
    if not attachment.content_type or not attachment.content_type.startswith("image/"):
        from app.core.exceptions import AppError

        raise AppError("整改附件必须是图片", "UPLOAD_INVALID_TYPE", 400)
    content = await attachment.read()
    stored_name, sha256, size_bytes = save_upload(content, attachment.content_type, settings.upload_dir, settings.max_upload_mb)
    upload = Upload(
        id=new_id("UPL"),
        project_id=order.project_id,
        uploaded_by=user.id,
        original_name=Path(attachment.filename or "attachment.jpg").name,
        stored_name=stored_name,
        mime_type=attachment.content_type,
        size_bytes=size_bytes,
        relative_path=f"uploads/{stored_name}",
        sha256=sha256,
    )
    db.add(upload)
    db.flush()
    db.add(WorkOrderEvent(id=new_id("WEO"), work_order_id=order.id, actor_user_id=user.id, event_type="attachment_added", from_status=order.status, to_status=order.status, note="上传整改附件", attachment_upload_id=upload.id))
    db.add(AuditLog(id=new_id("AUD"), user_id=user.id, action="attach_work_order_image", resource_type="work_order", resource_id=order.id, detail_json={"upload_id": upload.id}))
    db.commit()
    return ok({"work_order_id": order.id, "upload_id": upload.id, "filename": upload.original_name, "size_bytes": size_bytes, "stored": True, "file_url": f"/storage/{upload.relative_path}"}, http_request, "整改附件已保存")
