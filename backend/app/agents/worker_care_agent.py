from __future__ import annotations

from datetime import datetime, timezone

from app.providers.text.base import TextProvider
from app.workflow.state import WorkflowState


class WorkerCareAgent:
    name = "WorkerCareAgent"

    def __init__(self, provider: TextProvider) -> None:
        self.provider = provider

    def run(self, state: WorkflowState) -> dict[str, object]:
        started = datetime.now(timezone.utc)
        draft = state.get("work_order_draft") or {}
        message = self.provider.generate_worker_message(
            {
                "risk_level": draft.get("risk_level", state.get("risk_level", "medium")),
                "hazard_name": (state.get("hazards") or [{}])[0].get("hazard_name", "现场隐患"),
                "requirements": draft.get("rectification_requirements", []),
            }
        )
        draft["worker_message"] = message
        trace = {
            "agent": self.name,
            "status": "completed",
            "message": "已生成简短工友安全提醒",
            "started_at": started.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "duration_ms": 2,
        }
        return {"worker_message": message, "work_order_draft": draft, "agent_trace": [trace]}
