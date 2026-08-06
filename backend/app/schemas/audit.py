from __future__ import annotations

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    """审计日志条目（含操作人用户名，便于前端展示）。"""

    id: str
    user_id: str
    username: str | None
    action: str
    resource_type: str
    resource_id: str | None
    detail_json: dict[str, object]
    ip_address: str | None
    created_at: str


class AuditLogListResponse(BaseModel):
    """审计日志分页结果。"""

    items: list[AuditLogRead]
    total: int
    limit: int
    offset: int
