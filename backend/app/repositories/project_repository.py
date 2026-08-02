from sqlalchemy.orm import Session

from app.models import Project, ProjectMember


class ProjectRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_user(self, user_id: str) -> list[Project]:
        return (
            self.db.query(Project)
            .outerjoin(ProjectMember, ProjectMember.project_id == Project.id)
            .filter((Project.manager_user_id == user_id) | (ProjectMember.user_id == user_id))
            .order_by(Project.created_at.desc())
            .all()
        )

    def get(self, project_id: str) -> Project | None:
        return self.db.get(Project, project_id)
