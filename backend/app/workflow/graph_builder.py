from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agents.rag_agent import RagAgent
from app.agents.report_agent import ReportAgent
from app.agents.safety_agent import SafetyAgent
from app.agents.work_order_agent import WorkOrderAgent
from app.agents.worker_care_agent import WorkerCareAgent
from app.workflow.routing import next_route
from app.workflow.state import WorkflowState


def skip_downstream_agents(_: WorkflowState) -> dict[str, object]:
    return {
        "evidence": [],
        "work_order_draft": None,
        "worker_message": "",
        "agent_trace": [
            {"agent": "RagAgent", "status": "skipped", "message": "未发现隐患，跳过规范检索"},
            {"agent": "WorkOrderAgent", "status": "skipped", "message": "未发现隐患，跳过工单草稿"},
            {"agent": "WorkerCareAgent", "status": "skipped", "message": "未发现隐患，跳过工友提醒"},
        ],
    }


def build_graph(
    safety_agent: SafetyAgent,
    rag_agent: RagAgent,
    work_order_agent: WorkOrderAgent,
    worker_care_agent: WorkerCareAgent,
    report_agent: ReportAgent,
):
    graph = StateGraph(WorkflowState)
    graph.add_node("safety", safety_agent.run)
    graph.add_node("rag", rag_agent.run)
    graph.add_node("work_order", work_order_agent.run)
    graph.add_node("worker_care", worker_care_agent.run)
    graph.add_node("skip_downstream", skip_downstream_agents)
    graph.add_node("report", report_agent.run)
    graph.set_entry_point("safety")
    graph.add_conditional_edges("safety", next_route, {"hazards": "rag", "normal": "skip_downstream"})
    graph.add_edge("rag", "work_order")
    graph.add_edge("work_order", "worker_care")
    graph.add_edge("worker_care", "report")
    graph.add_edge("skip_downstream", "report")
    graph.add_edge("report", END)
    return graph.compile()

