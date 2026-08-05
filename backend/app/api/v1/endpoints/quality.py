from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import ensure_project_access, get_current_user
from app.api.response import ok
from app.db.session import get_db
from app.models import User
from app.services.quality_service import QualityService
from app.services.project_service import ProjectService


router = APIRouter(prefix="/quality", tags=["质量巡检"])


@router.get("/status")
def status(http_request: Request, user: User = Depends(get_current_user)):
    return ok({"key": "quality", "name": "工程质量巡检", "agent_name": "QualityAgent", "status": "available", "description": "质量缺陷识别（裂缝/渗漏/剥落/锈蚀/鼓包）五 Agent 闭环。", "planned_inputs": ["巡检图片", "位置", "作业类型"], "planned_outputs": ["缺陷清单", "质量整改工单草稿", "日报预览"], "available_endpoints": ["POST /api/v1/quality/analyze", "GET /api/v1/quality/tasks"]}, http_request)


@router.post("/analyze")
async def analyze(
    http_request: Request,
    image: UploadFile = File(...),
    project_id: str = Form(...),
    location: str = Form(...),
    work_type: str = Form(...),
    description: str = Form(""),
    demo_scenario: str | None = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_project_access(project_id, user, db)
    content = await image.read()
    data = QualityService(db).analyze(image_bytes=content, original_name=image.filename or "upload.jpg", content_type=image.content_type or "", project_id=project_id, location=location, work_type=work_type, description=description, demo_scenario=demo_scenario, requested_by=user.id)
    return ok(data.model_dump(mode="json"), http_request, "质量分析完成")


@router.get("/tasks")
def list_tasks(http_request: Request, project_id: str | None = Query(None), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if project_id:
        ensure_project_access(project_id, user, db)
        return ok(QualityService(db).list_tasks(project_id), http_request)
    project_ids = [project.id for project in ProjectService(db).list_for_user(user.id, user.role)]
    result = []
    service = QualityService(db)
    for visible_project_id in project_ids:
        result.extend(service.list_tasks(visible_project_id))
    return ok(result, http_request)


@router.get("/tasks/{task_id}")
def get_task(task_id: str, http_request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = QualityService(db).get_task(task_id)
    ensure_project_access(data.project_id, user, db)
    return ok(data.model_dump(mode="json"), http_request)
