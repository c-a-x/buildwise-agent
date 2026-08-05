from __future__ import annotations


class OpenAICompatibleSpeechProvider:
    """OpenAI-compatible 语音转写适配器（whisper 兼容 /audio/transcriptions）；离线模式不导入。"""

    name = "openai_compatible"

    _EXT_BY_MIME: dict[str, str] = {
        "audio/webm": "webm",
        "audio/ogg": "ogg",
        "audio/mp4": "mp4",
        "audio/mpeg": "mp3",
        "audio/wav": "wav",
        "audio/x-wav": "wav",
    }

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def _build_multipart(self, audio: bytes, mime: str, boundary: str) -> bytes:
        ext = self._EXT_BY_MIME.get(mime or "", "webm")
        head = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="voice.{ext}"\r\n'
            f"Content-Type: {mime or 'application/octet-stream'}\r\n\r\n"
        ).encode("utf-8")
        tail = (
            f"\r\n--{boundary}\r\n"
            f'Content-Disposition: form-data; name="model"\r\n\r\n'
            f"{self.model}\r\n"
            f"--{boundary}--\r\n"
        ).encode("utf-8")
        return head + audio + tail

    def transcribe(self, audio: bytes, mime: str) -> str:
        import json
        import uuid
        from urllib.request import Request, urlopen

        boundary = f"----buildwise{uuid.uuid4().hex}"
        body = self._build_multipart(audio, mime, boundary)
        request = Request(
            f"{self.base_url}/audio/transcriptions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        with urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        return str(data["text"])
