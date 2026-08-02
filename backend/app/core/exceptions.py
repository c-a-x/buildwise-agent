from __future__ import annotations

from typing import Any


class AppError(Exception):
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 400,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class NotFoundError(AppError):
    def __init__(self, message: str, code: str = "NOT_FOUND") -> None:
        super().__init__(message, code=code, status_code=404)


class ForbiddenError(AppError):
    def __init__(self, message: str = "没有权限执行此操作") -> None:
        super().__init__(message, code="AUTH_FORBIDDEN", status_code=403)
