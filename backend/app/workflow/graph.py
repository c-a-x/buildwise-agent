from __future__ import annotations

from pathlib import Path

from app.agents.rag_agent import RagAgent
from app.agents.report_agent import ReportAgent
from app.agents.safety_agent import SafetyAgent
from app.agents.work_order_agent import WorkOrderAgent
from app.agents.worker_care_agent import WorkerCareAgent
from app.core.config import Settings, settings as default_settings
from app.providers.factory import build_retrieval_provider, build_text_provider, build_vision_provider
from app.workflow.graph_builder import build_graph
from app.workflow.state import WorkflowState


class BuildWiseWorkflow:
    """Five deterministic business nodes compiled as a LangGraph state graph."""

    def __init__(self, knowledge_path: Path, runtime_settings: Settings) -> None:
        vision_provider = build_vision_provider(runtime_settings)
        retrieval_provider = build_retrieval_provider(runtime_settings)
        text_provider = build_text_provider(runtime_settings)
        self.provider_info = {
            "vision": getattr(vision_provider, "name", runtime_settings.vision_provider),
            "retrieval": getattr(retrieval_provider, "name", runtime_settings.retrieval_provider),
            "text": getattr(text_provider, "name", runtime_settings.text_provider),
        }
        self.graph = build_graph(
            SafetyAgent(vision_provider),
            RagAgent(retrieval_provider),
            WorkOrderAgent(),
            WorkerCareAgent(text_provider),
            ReportAgent(text_provider),
        )

    def run(self, initial_state: WorkflowState) -> WorkflowState:
        state = dict(initial_state)
        state["agent_trace"] = []
        result = self.graph.invoke(state)
        # 视觉节点(SafetyAgent)写入的是 provider 实际执行结果(如 safety_hybrid:yolo)，
        # 以此为准；不再用静态 provider 名字粗判，避免真实检测被误标为模拟。
        actual_vision = (result.get("provider_info") or {}).get("vision")
        result["provider_info"] = dict(self.provider_info)
        if actual_vision:
            result["provider_info"]["vision"] = actual_vision
        result["is_simulated"] = bool(result.get("is_simulated", True))
        result["review_required"] = True
        return result


def build_workflow(knowledge_path: Path, runtime_settings: Settings | None = None) -> BuildWiseWorkflow:
    return BuildWiseWorkflow(knowledge_path, runtime_settings or default_settings)
