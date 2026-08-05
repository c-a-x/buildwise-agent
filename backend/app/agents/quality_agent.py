from __future__ import annotations

from datetime import datetime, timezone

from app.providers.vision.base import VisionProvider
from app.workflow.state import WorkflowState


class QualityAgent:
    name = "QualityAgent"

    def __init__(self, provider: VisionProvider) -> None:
        self.provider = provider

    def run(self, state: WorkflowState) -> dict[str, object]:
        started = datetime.now(timezone.utc)
        result = self.provider.analyze(
            state.get("image_path", ""),
            {
                "demo_scenario": state.get("demo_scenario", "crack"),
                "work_type": state.get("work_type", ""),
                "location": state.get("location", ""),
            },
        )
        hazards = result.get("hazards", [])
        trace = {
            "agent": self.name,
            "status": "completed",
            "message": f"识别完成，发现 {len(hazards) if isinstance(hazards, list) else 0} 项缺陷",
            "started_at": started.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "duration_ms": 8,
        }
        provider_info: dict[str, str] = {"vision": str(result.get("provider", "quality_mock"))}
        llm_state = result.get("vision_llm")
        if isinstance(llm_state, dict):
            provider_info["vision_llm_provider"] = str(llm_state.get("provider") or "off")
            provider_info["vision_llm_enabled"] = str(bool(llm_state.get("enabled"))).lower()
            provider_info["vision_llm_hazards"] = str(int(llm_state.get("hazard_count") or 0))
        return {
            "hazards": hazards if isinstance(hazards, list) else [],
            "risk_level": str(result.get("risk_level", "normal")),
            "is_simulated": bool(result.get("is_simulated", True)),
            "provider_info": provider_info,
            "review_required": True,
            "agent_trace": [trace],
        }
