from __future__ import annotations

from app.core.exceptions import AppError


class EdgeTTSSpeechProvider:
    """edge-tts 语音合成（微软 Edge TTS 服务，需外网）。

    离线模式不强制导入 edge-tts；未安装或合成失败时由调用方降级为只推文字。
    """

    name = "edge_tts"
    is_simulated = False

    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural") -> None:
        self.voice = voice

    def synthesize(self, text: str) -> bytes:
        import asyncio

        try:
            import edge_tts
        except ImportError as exc:
            raise AppError(
                "未安装 edge-tts（pip install edge-tts），TTS 音频通道不可用",
                "PROVIDER_NOT_CONFIGURED",
                500,
            ) from exc

        buffer = bytearray()

        async def _run() -> None:
            communicate = edge_tts.Communicate(text, self.voice)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buffer.extend(chunk["data"])

        try:
            asyncio.run(_run())
        except AppError:
            raise
        except Exception as exc:
            raise AppError(f"TTS 合成失败：{exc}", "TTS_SYNTHESIS_FAILED", 500) from exc

        if not buffer:
            raise AppError("TTS 合成无输出", "TTS_SYNTHESIS_FAILED", 500)
        return bytes(buffer)
