from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.response import ok
from app.core.exceptions import ForbiddenError
from app.db.session import get_db
from app.models import User
from app.schemas.project import ProjectCreate, ProjectRead
from app.services.project_service import ProjectService


router = APIRouter(prefix="/projects", tags=["项目"])


@router.get("")
def list_projects(http_request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    projects = ProjectService(db).list_for_user(user.id, user.role)
    return ok([ProjectRead.model_validate(project).model_dump() for project in projects], http_request)


@router.post("")
def create_project(request: ProjectCreate, http_request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in {"admin", "project_manager"}:
        raise ForbiddenError("只有管理员或项目经理可以创建项目")
    project = ProjectService(db).create(request, user.id)
    return ok(ProjectRead.model_validate(project).model_dump(), http_request, "项目创建成功")


@router.get("/{project_id}")
def get_project(project_id: str, http_request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = ProjectService(db).get_for_user(project_id, user.id, user.role)
    return ok(ProjectRead.model_validate(project).model_dump(), http_request)
