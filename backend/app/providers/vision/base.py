from __future__ import annotations

from typing import Protocol


class VisionProvider(Protocol):
    def analyze(self, image_path: str, context: dict[str, str]) -> dict[str, object]:
        ...
