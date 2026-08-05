"""quality_hybrid 视觉 Provider：合并质量 YOLO 检测 + 质量 LLM 缺陷分析。

能力组合：
- YOLO（MBDD2025 训练，5 类缺陷）：目标检测，输出带 bbox/confidence 的缺陷
- LLM（QualityLLMHazardAnalyzer）：多模态分析，输出 D1-D5 深层缺陷与修复建议

降级规则（AGENTS.md：默认离线、模拟结果必须标记）：
- YOLO 可用或 LLM 成功执行 → is_simulated=False，provider 标注实际来源
- 两者都不可用 → 回退 QualityMockVisionProvider 语义，is_simulated=True
"""

from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.providers.vision.llm import QualityLLMHazardAnalyzer
from app.providers.vision.mapping import compute_risk_level, merge_hazards
from app.providers.vision.quality_mapping import class_to_defect
from app.providers.vision.quality_mock import QualityMockVisionProvider
from app.providers.vision.yolo import load_model


class QualityYOLODetector:
    """封装单次推理：图片路径 → 质量缺陷 hazard 列表（按 YOLO 类别 id 映射）。"""

    def __init__(self, model_path: str, conf_threshold: float = 0.45) -> None:
        self.model_path = model_path
        self.conf_threshold = conf_threshold

    @property
    def available(self) -> bool:
        """模型是否成功加载（区别于"检测不到缺陷"）。"""
        return load_model(self.model_path) is not None

    def detect(self, image_path: str) -> list[dict[str, Any]]:
        model = load_model(self.model_path)
        if model is None:
            return []
        try:
            results = model(image_path, verbose=False, conf=self.conf_threshold)
        except Exception:
            return []

        defects: list[dict[str, Any]] = []
        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            shape = getattr(result, "orig_shape", None)
            if not isinstance(shape, (tuple, list)) or len(shape) < 2:
                continue
            height = float(shape[0])
            width = float(shape[1])
            if height <= 0 or width <= 0:
                continue
            for box, confidence, class_id in zip(boxes.xyxy.tolist(), boxes.conf.tolist(), boxes.cls.tolist()):
                x1, y1, x2, y2 = (float(value) for value in box)
                normalized_bbox = [x1 / width, y1 / height, x2 / width, y2 / height]
                defect = class_to_defect(int(class_id), float(confidence), normalized_bbox)
                if defect is not None:
                    defects.append(defect)
        return defects


class QualityHybridVisionProvider:
    name = "quality_hybrid"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.yolo = QualityYOLODetector(str(settings.quality_model_path), settings.quality_conf_threshold)
        self.llm = QualityLLMHazardAnalyzer(settings)

    def analyze(self, image_path: str, context: dict[str, str]) -> dict[str, object]:
        yolo_ok = self.yolo.available
        llm_hazards, llm_ok = self.llm.analyze_sync(image_path)

        if not yolo_ok and not llm_ok:
            # 两个真实来源都不可用：回退模拟，保留离线可演示语义
            return QualityMockVisionProvider().analyze(image_path, context)

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
            "vision_llm": {
                "provider": self.llm.provider,
                "enabled": llm_ok,
                "hazard_count": len(llm_hazards),
            },
        }
