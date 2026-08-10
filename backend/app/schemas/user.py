from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.auth import UserRead


class UserProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    real_name: str | None = Field(default=None, min_length=1, max_length=64)
    phone: str | None = Field(default=None, max_length=32)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    new_password_confirm: str = Field(min_length=8, max_length=128)

    @field_validator("new_password_confirm")
    @classmethod
    def validate_password_confirm(cls, value: str, info):
        new_password = info.data.get("new_password")
        if new_password and new_password != value:
            raise ValueError("两次输入的新密码不一致")
        return value


__all__ = ["PasswordChangeRequest", "UserProfileUpdate", "UserRead"]
