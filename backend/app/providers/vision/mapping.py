"""Label / finding → buildwise hazard 的映射与合并逻辑。

`safety_hybrid` 视觉 Provider 把 YOLO 目标检测（safehat_identify）与
多模态 LLM 隐患分析（safety-scout）两类来源统一映射为 buildwise 的
hazard 结构：hazard_type / hazard_name / description / confidence /
risk_level / bbox（归一化 [left, top, right, bottom]，0~1）。
"""

from __future__ import annotations

from typing import Any

_RISK_ORDER: dict[str, int] = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "normal": 0,
}


def _normalize_risk(value: Any) -> str:
    """把任意来源的严重度归一化为 buildwise 风险等级。"""
    text = str(value or "").strip().lower()
    if text in _RISK_ORDER:
        return text
    aliases = {
        "严重": "high",
        "重大": "high",
        "较大": "medium",
        "一般": "low",
        "轻": "low",
        "无": "normal",
    }
    for alias, level in aliases.items():
        if alias in text:
            return level
    return "medium"


# YOLO label（小写）→ (hazard_type, 中文名称, risk_level)。
# 同时覆盖 safehat 10 类微调模型与 COCO 预训练模型。
# 合规类别（Hardhat/Mask/Safety Vest/Safety Cone）不映射为隐患。
YOLO_CLASS_MAP: dict[str, tuple[str, str, str]] = {
    "no-hardhat": ("no_helmet", "未佩戴安全帽", "high"),
    "no-mask": ("no_mask", "未佩戴口罩", "medium"),
    "no-safety vest": ("no_safety_vest", "未穿反光安全背心", "medium"),
    "person": ("person_present", "现场人员", "low"),
    "machinery": ("machinery_present", "现场机械", "low"),
    "vehicle": ("vehicle_present", "现场车辆", "low"),
}


def class_to_hazard(label: str, confidence: float, bbox: list[float]) -> dict[str, Any] | None:
    """单个 YOLO 检测框 → buildwise hazard；合规类别或未知类别返回 None。"""
    mapping = YOLO_CLASS_MAP.get(str(label or "").strip().lower())
    if mapping is None:
        return None
    hazard_type, hazard_name, risk_level = mapping
    return {
        "hazard_type": hazard_type,
        "hazard_name": hazard_name,
        "description": f"检测到 {label}（置信度 {confidence:.0%}）。",
        "confidence": round(float(confidence), 4),
        "risk_level": risk_level,
        "bbox": [float(value) for value in bbox],
    }


def llm_finding_to_hazard(finding: dict[str, Any]) -> dict[str, Any]:
    """LLM 输出的隐患条目 → buildwise hazard。

    LLM 期望字段（对齐 safety-scout 的 H1-H10 结构）：
    category_code(H1..H10) / category_name / description / severity /
    regulation / suggestion / confidence / is_major / major_basis。
    regulation 与 suggestion 不新增 schema 字段，并入 description。
    """
    code = str(finding.get("category_code", "")).strip()
    description = str(finding.get("description", "")).strip()
    regulation = str(finding.get("regulation", "")).strip()
    suggestion = str(finding.get("suggestion", "")).strip()
    major_basis = str(finding.get("major_basis", "")).strip()

    detail = description
    if regulation:
        detail = f"{detail}；规范依据：{regulation}"
    if suggestion:
        detail = f"{detail}；整改建议：{suggestion}"
    if finding.get("is_major") and major_basis:
        detail = f"{detail}；重大事故隐患判定：{major_basis}"

    hazard_type = f"llm_{code.lower()}" if code.startswith("H") else "llm_finding"
    return {
        "hazard_type": hazard_type,
        "hazard_name": str(finding.get("category_name") or "现场隐患"),
        "description": detail or "未提供具体描述",
        "confidence": round(float(finding.get("confidence") or 0.85), 4),
        "risk_level": _normalize_risk(finding.get("severity")),
        "bbox": None,
    }


def _bbox_center(bbox: list[float] | None) -> tuple[float, float] | None:
    if not bbox or len(bbox) < 4:
        return None
    return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)


def _same_detection(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """同 hazard_type 且 bbox 中心距离小于 0.15 视为同一条检测。"""
    if left.get("hazard_type") != right.get("hazard_type"):
        return False
    left_center = _bbox_center(left.get("bbox"))
    right_center = _bbox_center(right.get("bbox"))
    if left_center is None or right_center is None:
        return True  # 缺 bbox（LLM 来源）按类型合并
    return ((left_center[0] - right_center[0]) ** 2 + (left_center[1] - right_center[1]) ** 2) ** 0.5 < 0.15


def merge_hazards(yolo_hazards: list[dict[str, Any]], llm_hazards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """合并 YOLO 与 LLM 两类 hazard，按类型 + bbox 去重，保留置信度高者。"""
    merged: list[dict[str, Any]] = []
    for hazard in list(yolo_hazards) + list(llm_hazards):
        replaced = False
        for index, existing in enumerate(merged):
            if _same_detection(existing, hazard):
                if float(hazard.get("confidence", 0.0)) > float(existing.get("confidence", 0.0)):
                    merged[index] = hazard
                replaced = True
                break
        if not replaced:
            merged.append(hazard)
    return merged


def compute_risk_level(hazards: list[dict[str, Any]]) -> str:
    """取 hazards 中的最高风险等级；空列表返回 normal。"""
    highest = "normal"
    for hazard in hazards:
        level = _normalize_risk(hazard.get("risk_level"))
        if _RISK_ORDER[level] > _RISK_ORDER[highest]:
            highest = level
    return highest
