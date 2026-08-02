from __future__ import annotations


class UltralyticsVisionProvider:
    """Optional adapter placeholder; MVP deliberately stays offline."""

    name = "ultralytics"

    def analyze(self, image_path: str, context: dict[str, str]) -> dict[str, object]:
        raise RuntimeError("真实视觉 Provider 尚未安装，请使用 VISION_PROVIDER=mock")
