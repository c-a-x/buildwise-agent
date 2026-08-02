from __future__ import annotations

from datetime import datetime, timezone

from app.providers.vision.base import VisionProvider
from app.workflow.state import WorkflowState


class SafetyAgent:
    name = "SafetyAgent"

    def __init__(self, provider: VisionProvider) -> None:
        self.provider = provider

    def run(self, state: WorkflowState) -> dict[str, object]:
        started = datetime.now(timezone.utc)
        result = self.provider.analyze(
            state.get("image_path", ""),
            {
                "demo_scenario": state.get("demo_scenario", "no_helmet"),
                "work_type": state.get("work_type", ""),
                "location": state.get("location", ""),
            },
        )
        hazards = result.get("hazards", [])
        trace = {
            "agent": self.name,
            "status": "completed",
            "message": f"识别完成，发现 {len(hazards) if isinstance(hazards, list) else 0} 项隐患",
            "started_at": started.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "duration_ms": 8,
        }
        return {
            "hazards": hazards if isinstance(hazards, list) else [],
            "risk_level": str(result.get("risk_level", "normal")),
            "is_simulated": bool(result.get("is_simulated", True)),
            "provider_info": {"vision": str(result.get("provider", "mock"))},
            "review_required": True,
            "agent_trace": [trace],
        }
