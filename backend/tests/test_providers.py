from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.exceptions import AppError
from app.providers.factory import build_retrieval_provider, build_text_provider, build_vision_provider
from app.providers.retrieval.local_keyword import LocalKeywordRetrievalProvider
from app.providers.text.template import TemplateTextProvider
from app.providers.vision.mock import MockVisionProvider
from app.workflow.graph import build_workflow


def test_default_factory_returns_offline_providers():
    # 显式指定离线文本 Provider：类默认值在 import 时从 .env 求值，无法在测试期隔离
    settings = Settings(text_provider="template")

    assert isinstance(build_vision_provider(settings), MockVisionProvider)
    assert isinstance(build_retrieval_provider(settings), LocalKeywordRetrievalProvider)
    assert isinstance(build_text_provider(settings), TemplateTextProvider)


def test_factory_rejects_unknown_provider_name():
    settings = Settings(vision_provider="unknown")

    with pytest.raises(AppError, match="不支持的视觉 Provider") as error:
        build_vision_provider(settings)

    assert error.value.code == "PROVIDER_NOT_SUPPORTED"


def test_factory_rejects_unconfigured_optional_text_provider():
    # 显式置空 LLM 配置：断言缺 key 报错，不依赖 .env
    settings = Settings(
        text_provider="openai_compatible",
        llm_base_url="",
        llm_api_key="",
        llm_model="",
    )

    with pytest.raises(AppError, match="TEXT_PROVIDER") as error:
        build_text_provider(settings)

    assert error.value.code == "PROVIDER_NOT_CONFIGURED"


def test_workflow_exposes_compiled_langgraph(tmp_path: Path):
    workflow = build_workflow(tmp_path / "standards.json", Settings())

    assert workflow.graph is not None

