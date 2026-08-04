from app.workflow.state import WorkflowState


def next_route(state: WorkflowState) -> str:
    return "hazards" if state.get("hazards") else "normal"
