from __future__ import annotations

from datetime import datetime, timezone

from app.providers.text.base import TextProvider
from app.workflow.state import WorkflowState


class ReportAgent:
    name = "ReportAgent"

    def __init__(self, provider: TextProvider) -> None:
        self.provider = provider

    def run(self, state: WorkflowState) -> dict[str, object]:
        started = datetime.now(timezone.utc)
        hazards = state.get("hazards", [])
        if hazards:
            preview = f"本次分析发现 {len(hazards)} 项隐患，综合风险等级为 {state.get('risk_level', 'normal')}，已生成整改草稿，等待人工确认。"
        else:
            preview = "本次分析未发现新增隐患，仍需结合现场管理要求进行人工复核。"
        trace = {
            "agent": self.name,
            "status": "completed",
            "message": "已生成日报预览",
            "started_at": started.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "duration_ms": 2,
        }
        return {"report_preview": preview, "agent_trace": [trace]}
