from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.common import RiskLevel, WorkOrderStatus


class WorkOrderCreate(BaseModel):
    task_id: str
    assignee_user_id: str | None = None
    deadline: datetime | None = None
    confirm_ai_draft: bool = False


class WorkOrderStatusUpdate(BaseModel):
    status: WorkOrderStatus
    note: str = ""


class WorkOrderEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    from_status: str | None
    to_status: str | None
    note: str
    actor_user_id: str
    created_at: datetime


class WorkOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    incident_id: str
    source_task_id: str
    title: str
    problem_description: str
    risk_level: RiskLevel
    location: str
    assignee_user_id: str
    created_by: str
    deadline: datetime
    status: WorkOrderStatus
    rectification_requirements: list[str]
    review_requirements: list[str]
    worker_message: str
    ai_generated: bool
    confirmed_by_human: bool
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    events: list[WorkOrderEventRead] = []
    file_url: str | None = None
    annotated_url: str | None = None
    evidence: list[dict[str, object]] = []
