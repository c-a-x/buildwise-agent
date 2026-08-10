from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, UserRead
from app.schemas.user import PasswordChangeRequest, UserProfileUpdate
from app.services.audit_service import record_audit


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

    def refresh(self, user: User, *, ip_address: str | None = None) -> dict[str, object]:
        try:
            token = create_access_token(user.id)
            record_audit(
                self.db,
                user_id=user.id,
                action="token_refresh",
                resource_type="auth",
                resource_id=user.id,
                detail_json={},
                ip_address=ip_address,
                commit=False,
            )
            self.db.commit()
            return {"access_token": token, "token_type": "bearer", "expires_in": 120 * 60}
        except Exception:
            self.db.rollback()
            raise

    def update_profile(self, user: User, request: UserProfileUpdate, *, ip_address: str | None = None) -> UserRead:
        try:
            changes = request.model_dump(exclude_unset=True)
            if not changes:
                raise AppError("至少填写一项资料", "AUTH_PROFILE_EMPTY", 400)
            if "real_name" in changes:
                user.real_name = changes["real_name"]
            if "phone" in changes:
                user.phone = changes["phone"]
            self.db.flush()
            self.db.refresh(user)
            data = UserRead.model_validate(user)
            record_audit(
                self.db,
                user_id=user.id,
                action="update_profile",
                resource_type="user",
                resource_id=user.id,
                detail_json={"fields": sorted(changes)},
                ip_address=ip_address,
                commit=False,
            )
            self.db.commit()
            return data
        except Exception:
            self.db.rollback()
            raise

    def change_password(self, user: User, request: PasswordChangeRequest, *, ip_address: str | None = None) -> None:
        try:
            if not verify_password(request.current_password, user.password_hash):
                raise AppError("当前密码错误", "AUTH_CURRENT_PASSWORD_INVALID", 400)
            user.password_hash = hash_password(request.new_password)
            self.db.flush()
            record_audit(
                self.db,
                user_id=user.id,
                action="change_password",
                resource_type="user",
                resource_id=user.id,
                detail_json={},
                ip_address=ip_address,
                commit=False,
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
