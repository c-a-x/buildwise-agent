from __future__ import annotations

from app.agents.rag_agent import RagAgent
from app.agents.report_agent import ReportAgent
from app.agents.safety_agent import SafetyAgent
from app.agents.work_order_agent import WorkOrderAgent
from app.agents.worker_care_agent import WorkerCareAgent
from app.providers.retrieval.local_keyword import LocalKeywordRetrievalProvider
from app.providers.text.template import TemplateTextProvider
from app.providers.vision.mock import MockVisionProvider
from app.workflow.state import WorkflowState


class BuildWiseWorkflow:
    """LangGraph-compatible business sequence implemented offline for the MVP."""

    def __init__(self, knowledge_path):
        self.safety = SafetyAgent(MockVisionProvider())
        self.rag = RagAgent(LocalKeywordRetrievalProvider(knowledge_path))
        self.work_order = WorkOrderAgent()
        self.worker_care = WorkerCareAgent(TemplateTextProvider())
        self.report = ReportAgent(TemplateTextProvider())

    def run(self, initial_state: WorkflowState) -> WorkflowState:
        state: WorkflowState = dict(initial_state)
        state["agent_trace"] = []
        safety_output = self.safety.run(state)
        self._merge_output(state, safety_output)
        if state.get("hazards"):
            for agent in (self.rag, self.work_order, self.worker_care):
                output = agent.run(state)
                self._merge_output(state, output)
        else:
            state["evidence"] = []
            state["work_order_draft"] = None
            state["worker_message"] = ""
            state["agent_trace"] = state.get("agent_trace", []) + [
                {"agent": "RagAgent", "status": "skipped", "message": "未发现隐患，跳过规范检索"},
                {"agent": "WorkOrderAgent", "status": "skipped", "message": "未发现隐患，跳过工单草稿"},
                {"agent": "WorkerCareAgent", "status": "skipped", "message": "未发现隐患，跳过工友提醒"},
            ]
        report_output = self.report.run(state)
        self._merge_output(state, report_output)
        state["provider_info"] = {
            "vision": "mock",
            "retrieval": "local_keyword",
            "text": "template",
        }
        state["is_simulated"] = True
        state["review_required"] = True
        return state

    @staticmethod
    def _merge_output(state: WorkflowState, output: dict[str, object]) -> None:
        previous_trace = list(state.get("agent_trace", []))
        state.update({key: value for key, value in output.items() if key != "agent_trace"})
        state["agent_trace"] = previous_trace + list(output.get("agent_trace", []))


def build_workflow(knowledge_path):
    return BuildWiseWorkflow(knowledge_path)
