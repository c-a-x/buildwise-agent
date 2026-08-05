from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import AgentRunStatus, RiskLevel


# 与 safety 的 HazardRead 同构：质量语义只体现在字段值上（hazard_type=缺陷码、
# hazard_name=缺陷中文名、risk_level=严重度），保证五 agent 工作流零改动复用。
class QualityHazardRead(BaseModel):
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


class QualityEvidenceRead(BaseModel):
    id: str | None = None
    source: str
    article: str
    content: str
    score: float | None = None


class QualityAgentTraceItem(BaseModel):
    agent: str
    status: AgentRunStatus
    message: str
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int | None = None


class QualityWorkOrderDraft(BaseModel):
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


class QualityAnalysisResponse(BaseModel):
    task_id: str
    project_id: str
    upload_id: str
    file_url: str
    annotated_url: str | None = None
    location: str
    work_type: str
    risk_level: RiskLevel
    defects: list[QualityHazardRead]
    evidence: list[QualityEvidenceRead]
    work_order_draft: QualityWorkOrderDraft | None = None
    worker_message: str = ""
    report_preview: str = ""
    agent_trace: list[QualityAgentTraceItem]
    review_required: bool = True
    is_simulated: bool = True
    provider_info: dict[str, str]


class QualityTaskSummary(BaseModel):
    task_id: str
    project_id: str
    location: str
    work_type: str
    risk_level: RiskLevel
    status: AgentRunStatus
    incident_count: int
    is_simulated: bool
    created_at: str


class QualityAnalyzeForm(BaseModel):
    project_id: str
    location: str = Field(min_length=1, max_length=255)
    work_type: str = Field(min_length=1, max_length=128)
    description: str = ""
    demo_scenario: str | None = None
