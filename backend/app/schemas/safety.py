from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import AgentRunStatus, RiskLevel


class HazardRead(BaseModel):
    id: str
    hazard_type: str
    hazard_name: str
    description: str
    confidence: float
    risk_level: RiskLevel
    bbox: list[float] | None = None
    review_required: bool = True
    source: str | None = None
    regulation: str | None = None
    suggestion: str | None = None
    is_major: bool | None = None
    major_basis: str | None = None


class EvidenceRead(BaseModel):
    id: str | None = None
    source: str
    article: str
    content: str
    score: float | None = None


class AgentTraceItem(BaseModel):
    agent: str
    status: AgentRunStatus
    message: str
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int | None = None


class WorkOrderDraft(BaseModel):
    task_id: str
    incident_id: str
    title: str
    problem_description: str
    risk_level: RiskLevel
    location: str
    deadline: str
    assignee_role: str
    rectification_requirements: list[str]
    review_requirements: list[str]
    worker_message: str
    ai_generated: bool = True
    confirmed_by_human: bool = False
    review_required: bool = True
    is_simulated: bool = True


class SafetyAnalysisResponse(BaseModel):
    task_id: str
    project_id: str
    upload_id: str
    file_url: str
    annotated_url: str | None = None
    location: str
    work_type: str
    risk_level: RiskLevel
    hazards: list[HazardRead]
    evidence: list[EvidenceRead]
    work_order_draft: WorkOrderDraft | None = None
    worker_message: str = ""
    report_preview: str = ""
    agent_trace: list[AgentTraceItem]
    review_required: bool = True
    is_simulated: bool = True
    provider_info: dict[str, str]


class SafetyTaskSummary(BaseModel):
    task_id: str
    project_id: str
    location: str
    work_type: str
    risk_level: RiskLevel
    status: AgentRunStatus
    incident_count: int
    is_simulated: bool
    created_at: str


class SafetyAnalyzeForm(BaseModel):
    project_id: str
    location: str = Field(min_length=1, max_length=255)
    work_type: str = Field(min_length=1, max_length=128)
    description: str = ""
    demo_scenario: str | None = None
