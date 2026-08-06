from __future__ import annotations

from typing import Protocol


class SpeechSynthesisProvider(Protocol):
    """语音合成 Provider 抽象：接收中文文本，返回音频字节流。"""

    name: str
    is_simulated: bool

    def synthesize(self, text: str) -> bytes:
        ...
