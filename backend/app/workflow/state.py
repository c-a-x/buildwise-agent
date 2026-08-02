from __future__ import annotations

from typing import TypedDict


class WorkflowState(TypedDict, total=False):
    task_id: str
    project_id: str
    upload_id: str
    image_path: str
    location: str
    work_type: str
    description: str
    requested_by: str
    demo_scenario: str
    hazards: list[dict[str, object]]
    risk_level: str
    evidence: list[dict[str, object]]
    work_order_draft: dict[str, object] | None
    worker_message: str
    report_preview: str
    agent_trace: list[dict[str, object]]
    review_required: bool
    is_simulated: bool
    provider_info: dict[str, str]
    errors: list[dict[str, object]]
