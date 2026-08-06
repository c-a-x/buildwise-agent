from __future__ import annotations

import struct


class MockTTSSpeechProvider:
    """占位 TTS Provider：返回一段最小有效静音 WAV，仅演示/测试推送通道。

    is_simulated=True，payload 会显式标记，接收方不应将其当作真实语音。
    """

    name = "mock"
    is_simulated = True

    _SAMPLE_RATE = 16000
    _DURATION_S = 0.1

    def synthesize(self, text: str) -> bytes:
        sample_count = int(self._SAMPLE_RATE * self._DURATION_S)
        data_size = sample_count * 2  # 16-bit mono
        header = b"".join(
            [
                b"RIFF",
                struct.pack("<I", 36 + data_size),
                b"WAVE",
                b"fmt ",
                struct.pack("<I", 16),
                struct.pack("<HHIIHH", 1, 1, self._SAMPLE_RATE, self._SAMPLE_RATE * 2, 2, 16),
                b"data",
                struct.pack("<I", data_size),
            ]
        )
        return header + b"\x00" * data_size
