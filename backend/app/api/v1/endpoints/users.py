from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.response import ok
from app.db.session import get_db
from app.models import User
from app.schemas.auth import UserRead
from app.schemas.user import PasswordChangeRequest, UserProfileUpdate
from app.services.audit_service import client_ip
from app.services.auth_service import AuthService


router = APIRouter(prefix="/users", tags=["用户"])


@router.get("/me")
def current_user(http_request: Request, user: User = Depends(get_current_user)):
    return ok(UserRead.model_validate(user).model_dump(), http_request)


@router.patch("/me")
def update_current_user(
    request: UserProfileUpdate,
    http_request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = AuthService(db).update_profile(user, request, ip_address=client_ip(http_request))
    return ok(data.model_dump(), http_request, "资料已更新")


@router.post("/me/password")
def change_current_user_password(
    request: PasswordChangeRequest,
    http_request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    AuthService(db).change_password(user, request, ip_address=client_ip(http_request))
    return ok({"changed": True}, http_request, "密码已更新")
