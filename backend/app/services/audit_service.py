from __future__ import annotations

from datetime import datetime
from typing import TypeAlias

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog, User
from app.utils.ids import new_id


JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]
AuditRecord: TypeAlias = dict[str, JsonValue]


def record_audit(
    db: Session,
    *,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    detail_json: JsonObject | None = None,
    ip_address: str | None = None,
    commit: bool = True,
) -> AuditLog:
    """写一条审计日志；默认提交，事务型调用方可延迟提交。"""
    row = AuditLog(
        id=new_id("AUD"),
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail_json=detail_json or {},
        ip_address=ip_address,
    )
    db.add(row)
    if commit:
        db.commit()
    return row


def client_ip(request: Request) -> str | None:
    """取请求客户端 IP；代理/测试环境下可能为 None。"""
    return request.client.host if request.client else None


class AuditService:
    """权限审计查询：按操作/用户/资源/时间过滤，分页返回并附操作人用户名。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self,
        *,
        user_id: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditRecord], int]:
        query = self.db.query(AuditLog)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if start_at:
            query = query.filter(AuditLog.created_at >= start_at)
        if end_at:
            query = query.filter(AuditLog.created_at <= end_at)
        total = query.count()
        rows = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
        items = [self._serialize(row) for row in rows]
        return items, total

    def actions(self) -> list[str]:
        rows = self.db.query(AuditLog.action).distinct().order_by(AuditLog.action).all()
        return [row[0] for row in rows]

    def _serialize(self, row: AuditLog) -> AuditRecord:
        user = self.db.get(User, row.user_id)
        return {
            "id": row.id,
            "user_id": row.user_id,
            "username": user.username if user else None,
            "action": row.action,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id,
            "detail_json": row.detail_json if isinstance(row.detail_json, dict) else {},
            "ip_address": row.ip_address,
            "created_at": row.created_at.isoformat(),
        }
