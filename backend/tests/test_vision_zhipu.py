"""智谱（bigmodel）GLM-4V 视觉 LLM 分支单元测试。

覆盖 zhipu 作为 VISION_LLM_PROVIDER 时的 OpenAI 兼容调用链：
- 成功解析：fake httpx.Client 返回合法 JSON → 映射为 llm_h* hazard、ok=True
- 降级：choices 缺失 / HTTP 异常 → ok=False（保持"只降级不抛出"语义）
- 配置兜底：VISION_LLM_* 未设时取 LLM_*
"""

from __future__ import annotations

from pathlib import Path

import httpx

import app.providers.vision.llm as llm_module
from app.core.config import Settings
from app.providers.vision.llm import LLMHazardAnalyzer

ZHIPU_BASE = "https://open.bigmodel.cn/api/paas/v4"


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


class _FakeClient:
    def __init__(self, payload: dict[str, object], error: Exception | None = None) -> None:
        self._payload = payload
        self._error = error
        self.last_url: str | None = None
        self.last_payload: dict[str, object] | None = None

    def __enter__(self) -> "_FakeClient":
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def post(self, url: str, json: dict[str, object], headers: dict[str, str]) -> _FakeResponse:
        if self._error is not None:
            raise self._error
        self.last_url = url
        self.last_payload = json
        self.last_headers = headers
        return _FakeResponse(self._payload)


def _analyzer(**overrides: object) -> LLMHazardAnalyzer:
    return LLMHazardAnalyzer(
        Settings(
            vision_llm_provider="zhipu",
            vision_llm_base_url=ZHIPU_BASE,
            vision_llm_api_key="test-key",
            vision_llm_model="glm-4v-flash",
            **overrides,
        )
    )


def _make_image(tmp_path: Path) -> str:
    image = tmp_path / "site.jpg"
    image.write_bytes(b"\xff\xd8\xff\xe0 fake jpeg bytes")
    return str(image)


def _ok_payload() -> dict[str, object]:
    content = (
        '{"hazards": [{"category_code": "H9", "category_name": "个人防护缺失", '
        '"description": "工人未佩戴安全帽", "severity": "high", '
        '"regulation": "《建筑施工安全检查标准》JGJ59-2011", '
        '"suggestion": "立即佩戴安全帽并复核入场教育", "confidence": 0.92}]}'
    )
    return {"choices": [{"message": {"content": content}}]}


def test_zhipu_analyze_parses_findings(monkeypatch, tmp_path):
    client = _FakeClient(_ok_payload())
    monkeypatch.setattr(llm_module.httpx, "Client", lambda timeout: client)

    hazards, ok = _analyzer().analyze_sync(_make_image(tmp_path))

    assert ok is True
    assert hazards and hazards[0]["hazard_type"] == "llm_h9"
    assert hazards[0]["description"] == "工人未佩戴安全帽"
    assert hazards[0]["risk_level"] == "high"
    assert hazards[0]["bbox"] is None
    # 请求确实打到了智谱 OpenAI 兼容 endpoint，且携带模型与 base64 图片
    assert client.last_url == f"{ZHIPU_BASE}/chat/completions"
    assert client.last_payload["model"] == "glm-4v-flash"
    assert client.last_headers["Authorization"] == "Bearer test-key"
    image_item = client.last_payload["messages"][1]["content"][0]["image_url"]["url"]
    assert image_item.startswith("data:image/jpeg;base64,")


def test_zhipu_analyze_empty_hazards_ok(monkeypatch, tmp_path):
    # 模型确认无隐患：返回 {"hazards": []}，仍视为成功执行
    client = _FakeClient({"choices": [{"message": {"content": '{"hazards": []}'}}]})
    monkeypatch.setattr(llm_module.httpx, "Client", lambda timeout: client)

    hazards, ok = _analyzer().analyze_sync(_make_image(tmp_path))

    assert ok is True
    assert hazards == []


def test_zhipu_analyze_missing_choices_degrades(monkeypatch, tmp_path):
    client = _FakeClient({"choices": []})
    monkeypatch.setattr(llm_module.httpx, "Client", lambda timeout: client)

    hazards, ok = _analyzer().analyze_sync(_make_image(tmp_path))

    assert ok is False
    assert hazards == []


def test_zhipu_analyze_http_error_degrades(monkeypatch, tmp_path):
    client = _FakeClient({}, error=httpx.ConnectError("boom"))
    monkeypatch.setattr(llm_module.httpx, "Client", lambda timeout: client)

    hazards, ok = _analyzer().analyze_sync(_make_image(tmp_path))

    assert ok is False
    assert hazards == []


def test_zhipu_analyze_missing_config_degrades(tmp_path):
    # 未配置 base_url/key/model → 不发起请求，直接降级
    analyzer = LLMHazardAnalyzer(
        Settings(vision_llm_provider="zhipu", vision_llm_base_url="", vision_llm_api_key="", vision_llm_model="")
    )
    hazards, ok = analyzer.analyze_sync(_make_image(tmp_path))
    assert ok is False
    assert hazards == []


def test_quality_zhipu_parses_d_category_codes(monkeypatch, tmp_path):
    # 质量域走 QualityLLMHazardAnalyzer：_parse_findings 需按 D 前缀过滤，
    # 避免 D1-D5 缺陷码被安全 H 分类过滤器误删（回归：GLM-4V 返回 D 码但结果为空）
    from app.providers.vision.llm import QualityLLMHazardAnalyzer

    content = (
        '{"hazards": [{"category_code": "D1", "category_name": "裂缝", '
        '"description": "墙面纵向裂缝", "severity": "high", '
        '"regulation": "《混凝土结构工程施工质量验收规范》GB50204-2015", '
        '"suggestion": "及时修补裂缝", "confidence": 0.9}]}'
    )
    client = _FakeClient({"choices": [{"message": {"content": content}}]})
    monkeypatch.setattr(llm_module.httpx, "Client", lambda timeout: client)

    analyzer = QualityLLMHazardAnalyzer(
        Settings(
            vision_llm_provider="zhipu",
            vision_llm_base_url=ZHIPU_BASE,
            vision_llm_api_key="test-key",
            vision_llm_model="glm-4v-flash",
        )
    )
    hazards, ok = analyzer.analyze_sync(_make_image(tmp_path))

    assert ok is True
    assert len(hazards) == 1
    assert hazards[0]["hazard_type"] == "llm_d1"
    assert hazards[0]["description"] == "墙面纵向裂缝"
    assert hazards[0]["bbox"] is None

