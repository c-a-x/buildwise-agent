"""YOLO 目标检测层（源自 safehat_identify）。

懒加载 ultralytics 模型：不安装依赖、没有权重文件时返回 None，不影响
buildwise 离线启动。模型在进程内单例缓存，避免每次分析重复加载。
"""

from __future__ import annotations

from pathlib import Path

from app.providers.vision.mapping import class_to_hazard

_model_cache: dict[str, object | None] = {}
_last_error: str = ""


def _yolo_module():
    try:
        from ultralytics import YOLO  # type: ignore
    except ImportError:
        return None
    return YOLO


def load_model(model_path: str) -> object | None:
    """按路径加载 YOLO 模型（进程内缓存）。失败返回 None。"""
    global _last_error
    key = str(model_path)
    if key in _model_cache:
        return _model_cache[key]

    yolo_cls = _yolo_module()
    if yolo_cls is None:
        _last_error = "未安装 ultralytics，请先执行 pip install -e \"backend[vision]\""
        _model_cache[key] = None
        return None

    resolved = Path(model_path)
    if not resolved.is_absolute():
        from app.core.config import BACKEND_DIR

        resolved = BACKEND_DIR / resolved
    if not resolved.exists():
        _last_error = f"YOLO 模型文件不存在：{resolved}"
        _model_cache[key] = None
        return None

    try:
        model = yolo_cls(str(resolved))
        _model_cache[key] = model
        _last_error = ""
    except Exception as exc:  # 模型加载失败只降级，不抛出
        _last_error = f"YOLO 模型加载失败：{exc}"
        _model_cache[key] = None
    return _model_cache[key]


def last_error() -> str:
    return _last_error


class YOLODetector:
    """封装单次推理：图片路径 → buildwise hazard 列表。"""

    def __init__(self, model_path: str, conf_threshold: float = 0.5) -> None:
        self.model_path = model_path
        self.conf_threshold = conf_threshold

    @property
    def available(self) -> bool:
        """模型是否成功加载（区别于"检测不到东西"）。"""
        return load_model(self.model_path) is not None

    def detect(self, image_path: str) -> list[dict]:
        model = load_model(self.model_path)
        if model is None:
            return []
        try:
            results = model(image_path, verbose=False, conf=self.conf_threshold)
        except Exception as exc:
            _last_error = f"YOLO 推理失败：{exc}"
            return []

        hazards: list[dict] = []
        for result in results:
            names = getattr(result, "names", {})
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
                label = str(names[int(class_id)])
                x1, y1, x2, y2 = (float(value) for value in box)
                normalized_bbox = [x1 / width, y1 / height, x2 / width, y2 / height]
                hazard = class_to_hazard(label, float(confidence), normalized_bbox)
                if hazard is not None:
                    hazards.append(hazard)
        return hazards


def detect(image_path: str, model_path: str, conf_threshold: float = 0.5) -> list[dict]:
    return YOLODetector(model_path, conf_threshold).detect(image_path)
