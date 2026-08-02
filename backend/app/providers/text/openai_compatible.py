from __future__ import annotations


class OpenAICompatibleTextProvider:
    """Optional adapter placeholder; never required for local startup."""

    name = "openai_compatible"

    def generate_worker_message(self, payload: dict[str, object]) -> str:
        raise RuntimeError("真实文本 Provider 尚未配置，请使用 TEXT_PROVIDER=template")

    def generate_report(self, payload: dict[str, object]) -> str:
        raise RuntimeError("真实文本 Provider 尚未配置，请使用 TEXT_PROVIDER=template")
