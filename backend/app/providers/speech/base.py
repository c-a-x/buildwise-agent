from __future__ import annotations

from typing import Protocol


class SpeechTranscriptionProvider(Protocol):
    """语音转写 Provider 抽象：接收音频字节流，返回转写文本。"""

    name: str

    def transcribe(self, audio: bytes, mime: str) -> str:
        ...
