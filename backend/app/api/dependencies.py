from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ForbiddenError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import Project, ProjectMember, User


bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise AppError("请先登录", "AUTH_TOKEN_EXPIRED", 401)
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise AppError("登录已失效，请重新登录", "AUTH_TOKEN_EXPIRED", 401) from exc
    user = db.get(User, str(payload["sub"]))
    if not user or not user.is_active:
        raise AppError("用户不存在或已停用", "AUTH_TOKEN_EXPIRED", 401)
    return user


def require_roles(*roles: str) -> Callable:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise ForbiddenError()
        return user

    return dependency


def ensure_project_access(project_id: str, user: User, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise AppError("项目不存在", "PROJECT_NOT_FOUND", 404)
    if user.role == "admin":
        return project
    member = db.query(ProjectMember).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user.id).first()
    if not member and project.manager_user_id != user.id:
        raise ForbiddenError("你不是该项目成员")
    return project
