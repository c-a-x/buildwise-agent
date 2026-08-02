from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, UserRead


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def register(self, request: RegisterRequest) -> UserRead:
        if self.users.get_by_username(request.username):
            raise AppError("用户名已存在", "AUTH_USERNAME_EXISTS", 409)
        user = User(
            username=request.username,
            real_name=request.real_name,
            password_hash=hash_password(request.password),
            role=request.role,
            phone=request.phone,
            is_active=True,
        )
        self.users.add(user)
        self.db.commit()
        return UserRead.model_validate(user)

    def login(self, request: LoginRequest) -> LoginResponse:
        user = self.users.get_by_username(request.username)
        if not user or not user.is_active or not verify_password(request.password, user.password_hash):
            raise AppError("用户名或密码错误", "AUTH_INVALID_CREDENTIALS", 401)
        token = create_access_token(user.id)
        return LoginResponse(
            access_token=token,
            expires_in=120 * 60,
            user=UserRead.model_validate(user),
        )
