"""质量缺陷检测 → buildwise hazard 的映射与合并逻辑。

`quality_hybrid` 视觉 Provider 把 YOLO 缺陷检测（MBDD2025 训练，5 类）与
可选 LLM 质量缺陷分析统一映射为 buildwise 的 hazard 结构
（hazard_type / hazard_name / description / confidence / risk_level / bbox），
从而让五 agent 工作流（RagAgent / WorkOrderAgent / ...）零改动复用。

内部字段继续用 hazard/risk_level 两个 key，质量语义只体现在字段值上：
hazard_type 存缺陷码（crack/leakage/abscission/corrosion/bulge），
hazard_name 存缺陷中文名，risk_level 存严重度。
"""

from __future__ import annotations

from typing import Any

from app.providers.vision.mapping import _normalize_risk
from app.rules.risk_rules import compute_risk_score

# YOLO 类别 id → (defect_type, 中文名, risk_level)。
# class id 顺序对齐 MBDD2025 Labels 与训练 data.yaml 的 names。
DEFECT_CLASS_MAP: dict[int, tuple[str, str, str]] = {
    0: ("crack", "裂缝", "medium"),
    1: ("leakage", "渗漏", "medium"),
    2: ("abscission", "剥落", "high"),
    3: ("corrosion", "锈蚀", "medium"),
    4: ("bulge", "鼓包", "high"),
}

DEFECT_TYPE_CN: dict[str, str] = {value[0]: value[1] for value in DEFECT_CLASS_MAP.values()}


def class_to_defect(class_id: int, confidence: float, bbox: list[float]) -> dict[str, Any] | None:
    """单个 YOLO 检测框（按类别 id）→ buildwise hazard；未知类别返回 None。"""
    mapping = DEFECT_CLASS_MAP.get(int(class_id))
    if mapping is None:
        return None
    defect_type, defect_name, risk_level = mapping
    return {
        "hazard_type": defect_type,
        "hazard_name": defect_name,
        "description": f"检测到墙体{defect_name}缺陷（置信度 {confidence:.0%}）。",
        "confidence": round(float(confidence), 4),
        "risk_level": risk_level,
        "risk_score": compute_risk_score(defect_type, risk_level, confidence=float(confidence)),
        "bbox": [float(value) for value in bbox],
        "source": "yolo",
    }


def quality_llm_finding_to_hazard(finding: dict[str, Any]) -> dict[str, Any]:
    """LLM 输出的质量缺陷条目 → buildwise hazard。

    LLM 期望字段（对齐 QUALITY_ANALYZE_PROMPT 的 D1-D5 结构）：
    category_code(D1..D5) / category_name / description / severity /
    regulation / suggestion / confidence / is_major / major_basis。
    """
    code = str(finding.get("category_code", "")).strip()
    description = str(finding.get("description", "")).strip() or "未提供具体描述"
    hazard_type = f"llm_{code.lower()}" if code.startswith("D") else "llm_defect"
    return {
        "hazard_type": hazard_type,
        "hazard_name": str(finding.get("category_name") or "质量缺陷"),
        "description": description,
        "confidence": round(float(finding.get("confidence") or 0.85), 4),
        "risk_level": _normalize_risk(finding.get("severity")),
        "risk_score": compute_risk_score(hazard_type, _normalize_risk(finding.get("severity")), confidence=float(finding.get("confidence") or 0.85), is_major=bool(finding.get("is_major"))),
        "bbox": None,
        "source": "llm",
        "regulation": str(finding.get("regulation", "")).strip(),
        "suggestion": str(finding.get("suggestion", "")).strip(),
        "is_major": bool(finding.get("is_major")),
        "major_basis": str(finding.get("major_basis", "")).strip(),
    }
