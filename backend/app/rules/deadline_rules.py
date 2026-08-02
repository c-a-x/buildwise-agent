def deadline_hours_for(risk_level: str) -> int:
    return {"critical": 2, "high": 4, "medium": 24, "low": 48, "normal": 72}.get(risk_level, 24)
