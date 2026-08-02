from __future__ import annotations

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel


T = TypeVar("T")
RiskLevel = Literal["normal", "low", "medium", "high", "critical"]
WorkOrderStatus = Literal["pending", "in_progress", "pending_review", "closed"]
AgentRunStatus = Literal["pending", "running", "completed", "failed", "skipped"]


class ApiEnvelope(BaseModel, Generic[T]):
    success: bool = True
    message: str = "success"
    data: T
    request_id: str


class ErrorBody(BaseModel):
    success: bool = False
    message: str
    error: dict[str, object]
    request_id: str
