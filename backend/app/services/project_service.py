from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ForbiddenError, NotFoundError
from app.models import Project, ProjectMember
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate


class ProjectService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.projects = ProjectRepository(db)

    def list_for_user(self, user_id: str, role: str) -> list[Project]:
        if role == "admin":
            return self.db.query(Project).order_by(Project.created_at.desc()).all()
        return self.projects.list_for_user(user_id)

    def get_for_user(self, project_id: str, user_id: str, role: str) -> Project:
        project = self.projects.get(project_id)
        if not project:
            raise NotFoundError("项目不存在", "PROJECT_NOT_FOUND")
        if role == "admin":
            return project
        member = (
            self.db.query(ProjectMember)
            .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
            .first()
        )
        if project.manager_user_id != user_id and not member:
            raise ForbiddenError("你不是该项目成员")
        return project

    def create(self, request: ProjectCreate, manager_user_id: str) -> Project:
        if self.db.query(Project).filter(Project.code == request.code).first():
            raise AppError("项目编码已存在", "PROJECT_CODE_EXISTS", 409)
        project = Project(
            code=request.code,
            name=request.name,
            address=request.address,
            description=request.description,
            manager_user_id=manager_user_id,
            status="active",
        )
        self.db.add(project)
        self.db.flush()
        self.db.add(ProjectMember(project_id=project.id, user_id=manager_user_id, project_role="manager"))
        self.db.commit()
        return project
