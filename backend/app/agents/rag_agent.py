from __future__ import annotations

from datetime import datetime, timezone

from app.providers.retrieval.base import RetrievalProvider
from app.workflow.state import WorkflowState


class RagAgent:
    name = "RagAgent"

    def __init__(self, provider: RetrievalProvider) -> None:
        self.provider = provider

    def run(self, state: WorkflowState) -> dict[str, object]:
        started = datetime.now(timezone.utc)
        hazards = state.get("hazards", [])
        evidence: list[dict[str, object]] = []
        for hazard in hazards:
            hazard_type = str(hazard.get("hazard_type", ""))
            query = " ".join(
                str(hazard.get(key, ""))
                for key in ("hazard_name", "description")
            )
            evidence.extend(self.provider.search(query, {"hazard_type": hazard_type}, top_k=3))
        trace = {
            "agent": self.name,
            "status": "completed",
            "message": f"检索到 {len(evidence)} 条规范依据" if evidence else "未检索到足够规范依据，待人工补充",
            "started_at": started.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "duration_ms": 5,
        }
        return {"evidence": evidence, "agent_trace": [trace]}
