from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.response import ok
from app.core.exceptions import AppError
from app.db.session import get_db
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, UserRead
from app.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register")
def register(request: RegisterRequest, http_request: Request, db: Session = Depends(get_db)):
    data = AuthService(db).register(request)
    return ok(data.model_dump(), http_request, "注册成功")


@router.post("/login")
def login(request: LoginRequest, http_request: Request, db: Session = Depends(get_db)):
    data = AuthService(db).login(request)
    return ok(data.model_dump(), http_request, "登录成功")


@router.get("/me")
def me(http_request: Request, user: User = Depends(get_current_user)):
    return ok(UserRead.model_validate(user).model_dump(), http_request)


@router.post("/logout")
def logout(http_request: Request, user: User = Depends(get_current_user)):
    return ok({"logged_out": True, "user_id": user.id}, http_request, "已退出登录")


@router.post("/refresh")
def refresh(http_request: Request, user: User = Depends(get_current_user)):
    from app.core.security import create_access_token

    return ok({"access_token": create_access_token(user.id), "token_type": "bearer", "expires_in": 120 * 60}, http_request)
