"""隐患风险评分规则。

`RISK_RULES` 提供具体隐患类型的基础分与整改责任/时限映射；
`compute_risk_score` 把 hazard_type / risk_level / confidence / is_major
折算为 0-100 的量化风险分，供安全/质量两条链路的 hazard 与工单展示。
未知类型（如 LLM 的 llm_h1..h10）回退到风险等级基础分。
"""

from __future__ import annotations

RISK_RULES: dict[str, dict[str, object]] = {
    "no_helmet": {"risk_level": "high", "base_score": 90, "assignee_role": "safety_officer", "deadline_hours": 4},
    "missing_guardrail": {"risk_level": "critical", "base_score": 98, "assignee_role": "project_manager", "deadline_hours": 2},
    "no_safety_vest": {"risk_level": "medium", "base_score": 65, "assignee_role": "safety_officer", "deadline_hours": 24},
}

# 风险等级兜底基础分：LLM 隐患 / 质量缺陷等不在 RISK_RULES 中的类型使用。
_LEVEL_BASE: dict[str, int] = {"critical": 95, "high": 80, "medium": 60, "low": 35, "normal": 20}


def compute_risk_score(
    hazard_type: str,
    risk_level: str,
    confidence: float = 1.0,
    is_major: bool = False,
    base_score: int | None = None,
) -> int:
    """把隐患折算为 0-100 风险分。

    基础分取 `RISK_RULES[type].base_score`，未命中时按风险等级兜底；
    置信度把分数向 70%~100% 区间缩放，重大隐患（is_major）额外 +12。
    """
    rule = RISK_RULES.get(hazard_type) if isinstance(RISK_RULES.get(hazard_type), dict) else None
    if base_score is None:
        base_score = rule.get("base_score") if rule else None
    base = base_score if isinstance(base_score, int) else _LEVEL_BASE.get(risk_level, 50)
    scaled = base * (0.7 + 0.3 * max(0.0, min(1.0, float(confidence))))
    score = scaled + (12 if is_major else 0)
    return int(round(max(0, min(100, score))))
