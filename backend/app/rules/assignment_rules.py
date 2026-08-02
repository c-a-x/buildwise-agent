def assignee_role_for(hazard_type: str) -> str:
    return {"missing_guardrail": "project_manager"}.get(hazard_type, "safety_officer")
