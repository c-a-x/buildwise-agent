"""safety_hybrid 视觉 Provider：合并 YOLO 检测 + LLM 隐患分析。

能力组合：
- YOLO（safehat_identify）：目标检测，输出带 bbox/confidence 的隐患
- LLM（safety-scout）：多模态分析，输出 H1-H10 深层隐患与整改建议

降级规则（AGENTS.md：默认离线、模拟结果必须标记）：
- YOLO 可用或 LLM 成功执行 → is_simulated=False，provider 标注实际来源
- 两者都不可用 → 回退 MockVisionProvider 语义，is_simulated=True
"""

from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.providers.vision.base import VisionProvider
from app.providers.vision.llm import LLMHazardAnalyzer
from app.providers.vision.mapping import compute_risk_level, merge_hazards
from app.providers.vision.mock import MockVisionProvider
from app.providers.vision.yolo import YOLODetector


class SafetyHybridVisionProvider:
    name = "safety_hybrid"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.yolo = YOLODetector(str(settings.yolo_model_path), settings.yolo_conf_threshold)
        self.llm = LLMHazardAnalyzer(settings)

    def analyze(self, image_path: str, context: dict[str, str]) -> dict[str, object]:
        yolo_ok = self.yolo.available
        llm_hazards, llm_ok = self.llm.analyze_sync(image_path)

        if not yolo_ok and not llm_ok:
            # 两个真实来源都不可用：回退模拟，保留离线可演示语义
            return MockVisionProvider().analyze(image_path, context)

        yolo_hazards: list[dict[str, Any]] = self.yolo.detect(image_path) if yolo_ok else []
        sources = []
        if yolo_ok:
            sources.append("yolo")
        if llm_ok:
            sources.append(str(self.llm.provider))

        hazards = merge_hazards(yolo_hazards, llm_hazards)
        risk_level = compute_risk_level(hazards)
        return {
            "hazards": hazards,
            "risk_level": risk_level,
            "is_simulated": False,
            "provider": f"{self.name}:{'+'.join(sources)}",
        }
