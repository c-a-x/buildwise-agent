from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from app.agents.rag_agent import RagAgent
from app.agents.report_agent import ReportAgent
from app.agents.safety_agent import SafetyAgent
from app.agents.work_order_agent import QUALITY_RULES, WorkOrderAgent
from app.agents.worker_care_agent import WorkerCareAgent
from app.core.config import Settings, settings as default_settings
from app.providers.factory import build_retrieval_provider, build_text_provider, build_vision_provider
from app.workflow.graph_builder import build_graph
from app.workflow.state import WorkflowState


class BuildWiseWorkflow:
    """Five deterministic business nodes compiled as a LangGraph state graph.

    module="safety"（默认）：安全五节点（SafetyAgent → RagAgent → ...）。
    module="quality"：质量缺陷五节点，复用同一 LangGraph 骨架与 hazard 状态结构，
    仅换入口 Agent（QualityAgent）、缺陷规则、角色词与质量规范知识库。
    """

    def __init__(self, knowledge_path: Path, runtime_settings: Settings, module: str = "safety") -> None:
        if module == "quality":
            from app.agents.quality_agent import QualityAgent
            from app.providers.vision.quality_hybrid import QualityHybridVisionProvider

            vision_provider = QualityHybridVisionProvider(runtime_settings)
            entry_agent = QualityAgent(vision_provider)
            entry_node = "quality"
            work_order_agent = WorkOrderAgent(QUALITY_RULES)
            role = "质检员"
            finding_label = "质量缺陷"
            # 质量规范用独立知识库；Chroma 模式仍共享同一个 collection（按 metadata 区分）
            retrieval_provider = build_retrieval_provider(
                replace(runtime_settings, knowledge_json_path=runtime_settings.quality_knowledge_json_path)
            )
        else:
            vision_provider = build_vision_provider(runtime_settings)
            entry_agent = SafetyAgent(vision_provider)
            entry_node = "safety"
            work_order_agent = WorkOrderAgent()
            role = "安全员"
            finding_label = "隐患"
            retrieval_provider = build_retrieval_provider(runtime_settings)

        text_provider = build_text_provider(runtime_settings)
        self.provider_info = {
            "vision": getattr(vision_provider, "name", runtime_settings.vision_provider),
            "retrieval": getattr(retrieval_provider, "name", runtime_settings.retrieval_provider),
            "text": getattr(text_provider, "name", runtime_settings.text_provider),
        }
        self.graph = build_graph(
            entry_agent,
            RagAgent(retrieval_provider),
            work_order_agent,
            WorkerCareAgent(text_provider, role=role),
            ReportAgent(text_provider, finding_label=finding_label),
            entry_node=entry_node,
            finding_label=finding_label,
        )

    def run(self, initial_state: WorkflowState) -> WorkflowState:
        state = dict(initial_state)
        state["agent_trace"] = []
        result = self.graph.invoke(state)
        # 视觉节点(入口 Agent)写入的是 provider 实际执行结果(如 quality_hybrid:yolo)，
        # 以此为准；不再用静态 provider 名字粗判，避免真实检测被误标为模拟。
        agent_provider_info = dict(result.get("provider_info") or {})
        actual_vision = agent_provider_info.get("vision")
        result["provider_info"] = dict(self.provider_info)
        if actual_vision:
            result["provider_info"]["vision"] = actual_vision
        # 保留 agent 提供的附加 provider 信息（如 vision_llm 启用状态）
        for key, value in agent_provider_info.items():
            if key != "vision":
                result["provider_info"][key] = str(value)
        result["is_simulated"] = bool(result.get("is_simulated", True))
        result["review_required"] = True
        return result


def build_workflow(knowledge_path: Path, runtime_settings: Settings | None = None, module: str = "safety") -> BuildWiseWorkflow:
    return BuildWiseWorkflow(knowledge_path, runtime_settings or default_settings, module=module)
