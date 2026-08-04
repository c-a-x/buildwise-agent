from __future__ import annotations


class UltralyticsVisionProvider:
    """Optional lazy-loaded YOLO adapter; it never affects offline startup."""

    name = "ultralytics"

    def __init__(self, model_path: str) -> None:
        self.model_path = model_path

    def analyze(self, image_path: str, context: dict[str, str]) -> dict[str, object]:
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError("真实视觉 Provider 未安装，请使用 VISION_PROVIDER=mock") from exc
        model = YOLO(self.model_path)
        results = model(image_path, verbose=False)
        hazards: list[dict[str, object]] = []
        for result in results:
            names = result.names
            boxes = result.boxes
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
                label = str(names[int(class_id)])
                hazard_type = {"no_helmet": "no_helmet", "missing_guardrail": "missing_guardrail", "no_safety_vest": "no_safety_vest"}.get(label)
                if not hazard_type:
                    continue
                x1, y1, x2, y2 = (float(value) for value in box)
                hazards.append({"hazard_type": hazard_type, "hazard_name": label, "description": f"检测到 {label}。", "confidence": float(confidence), "risk_level": "high", "bbox": [x1 / width, y1 / height, x2 / width, y2 / height]})
        return {"hazards": hazards, "risk_level": "high" if hazards else "normal", "is_simulated": False, "provider": self.name}
