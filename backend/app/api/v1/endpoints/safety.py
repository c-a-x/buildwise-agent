from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import ensure_project_access, get_current_user
from app.api.response import ok
from app.db.session import get_db
from app.models import User
from app.services.safety_service import SafetyService


router = APIRouter(prefix="/safety", tags=["安全分析"])


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
    data = SafetyService(db).analyze(image_bytes=content, original_name=image.filename or "upload.jpg", content_type=image.content_type or "", project_id=project_id, location=location, work_type=work_type, description=description, demo_scenario=demo_scenario, requested_by=user.id)
    return ok(data.model_dump(mode="json"), http_request, "安全分析完成")


@router.get("/tasks")
def list_tasks(http_request: Request, project_id: str | None = Query(None), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if project_id:
        ensure_project_access(project_id, user, db)
    else:
        project_ids = [project.id for project in __import__("app.services.project_service", fromlist=["ProjectService"]).ProjectService(db).list_for_user(user.id, user.role)]
        # The service query accepts an optional project; merge visible tasks for non-admin users.
        result = []
        service = SafetyService(db)
        for visible_project_id in project_ids:
            result.extend(service.list_tasks(visible_project_id))
        return ok(result, http_request)
    return ok(SafetyService(db).list_tasks(project_id), http_request)


@router.get("/tasks/{task_id}")
def get_task(task_id: str, http_request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = SafetyService(db).get_task(task_id)
    ensure_project_access(data.project_id, user, db)
    return ok(data.model_dump(mode="json"), http_request)
