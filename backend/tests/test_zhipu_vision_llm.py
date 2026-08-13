from __future__ import annotations

import json

from app.core.config import Settings
from app.providers.vision.llm import LLMHazardAnalyzer


class _FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "hazards": [
                                    {
                                        "category_code": "H9",
                                        "category_name": "个人防护缺失",
                                        "description": "现场作业人员未正确佩戴安全帽。",
                                        "severity": "high",
                                        "confidence": 0.91,
                                    }
                                ]
                            },
                            ensure_ascii=False,
                        )
                    }
                }
            ]
        }


def test_zhipu_vision_llm_uses_dedicated_credentials(monkeypatch, tmp_path):
    image = tmp_path / "site.jpg"
    image.write_bytes(b"fake-image")
    captured = {}

    class FakeClient:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def post(self, url, json=None, headers=None):
            captured["url"] = url
            captured["payload"] = json
            captured["authorization"] = (headers or {}).get("Authorization")
            return _FakeResponse()

    monkeypatch.setattr("app.providers.vision.llm.httpx.Client", FakeClient)
    settings = Settings(
        vision_llm_provider="zhipu",
        vision_llm_base_url="https://open.bigmodel.cn/api/paas/v4",
        vision_llm_api_key="vision-key",
        vision_llm_model="glm-4v-flash",
        llm_base_url="https://text.example/v1",
        llm_api_key="text-key",
        llm_model="text-model",
        vision_llm_timeout=12,
    )

    hazards, ok = LLMHazardAnalyzer(settings).analyze_sync(str(image))

    assert ok is True
    assert captured["url"] == "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    assert captured["authorization"] == "Bearer vision-key"
    assert captured["payload"]["model"] == "glm-4v-flash"
    assert hazards[0]["hazard_type"] == "llm_h9"
    assert hazards[0]["source"] == "llm"
