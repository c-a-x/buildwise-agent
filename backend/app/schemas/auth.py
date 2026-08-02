from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Role = Literal["admin", "project_manager", "safety_officer", "quality_inspector", "worker"]


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_\-]+$")
    real_name: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    password_confirm: str = Field(min_length=8, max_length=128)
    role: Literal["project_manager", "safety_officer", "quality_inspector", "worker"]
    phone: str | None = Field(default=None, max_length=32)

    @field_validator("password_confirm")
    @classmethod
    def validate_password_confirm(cls, value: str, info):
        password = info.data.get("password")
        if password and password != value:
            raise ValueError("两次输入的密码不一致")
        return value


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)
    remember: bool = False


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    real_name: str
    role: Role
    phone: str | None = None
    is_active: bool


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead
