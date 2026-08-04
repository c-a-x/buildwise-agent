from __future__ import annotations


class OpenAICompatibleTextProvider:
    """Minimal OpenAI-compatible adapter; never imported in offline mode."""

    name = "openai_compatible"

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def _generate(self, prompt: str) -> str:
        import json
        from urllib.request import Request, urlopen

        payload = json.dumps({"model": self.model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1}).encode("utf-8")
        request = Request(f"{self.base_url}/chat/completions", data=payload, headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        return str(data["choices"][0]["message"]["content"])

    def generate_worker_message(self, payload: dict[str, object]) -> str:
        return self._generate(f"请将以下施工安全要求转为不超过100字、尊重且明确的工友提醒：{payload}")

    def generate_report(self, payload: dict[str, object]) -> str:
        return self._generate(f"请根据以下结构化统计生成项目安全日报，不要修改任何数字：{payload}")
