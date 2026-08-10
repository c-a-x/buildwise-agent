from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.response import ok
from app.db.session import get_db
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, UserRead
from app.services.auth_service import AuthService
from app.services.audit_service import client_ip, record_audit


router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register")
def register(request: RegisterRequest, http_request: Request, db: Session = Depends(get_db)):
    data = AuthService(db).register(request)
    return ok(data.model_dump(), http_request, "注册成功")


@router.post("/login")
def login(request: LoginRequest, http_request: Request, db: Session = Depends(get_db)):
    data = AuthService(db).login(request)
    user = db.query(User).filter(User.username == request.username).first()
    if user:
        record_audit(db, user_id=user.id, action="user_login", resource_type="auth", resource_id=user.id, detail_json={"username": user.username}, ip_address=client_ip(http_request))
    return ok(data.model_dump(), http_request, "登录成功")


@router.get("/me")
def me(http_request: Request, user: User = Depends(get_current_user)):
    return ok(UserRead.model_validate(user).model_dump(), http_request)


@router.post("/logout")
def logout(http_request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record_audit(db, user_id=user.id, action="user_logout", resource_type="auth", resource_id=user.id, detail_json={"username": user.username}, ip_address=client_ip(http_request))
    return ok({"logged_out": True, "user_id": user.id}, http_request, "已退出登录")


@router.post("/refresh")
def refresh(http_request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = AuthService(db).refresh(user, ip_address=client_ip(http_request))
    return ok(data, http_request)
