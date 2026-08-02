from app.workflow.state import WorkflowState


def next_route(state: WorkflowState) -> str:
    return "rag" if state.get("hazards") else "report"
