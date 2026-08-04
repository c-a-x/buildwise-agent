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
    settings = Settings()

    assert isinstance(build_vision_provider(settings), MockVisionProvider)
    assert isinstance(build_retrieval_provider(settings), LocalKeywordRetrievalProvider)
    assert isinstance(build_text_provider(settings), TemplateTextProvider)


def test_factory_rejects_unknown_provider_name():
    settings = Settings(vision_provider="unknown")

    with pytest.raises(AppError, match="不支持的视觉 Provider") as error:
        build_vision_provider(settings)

    assert error.value.code == "PROVIDER_NOT_SUPPORTED"


def test_factory_rejects_unconfigured_optional_text_provider():
    settings = Settings(text_provider="openai_compatible")

    with pytest.raises(AppError, match="TEXT_PROVIDER") as error:
        build_text_provider(settings)

    assert error.value.code == "PROVIDER_NOT_CONFIGURED"


def test_workflow_exposes_compiled_langgraph(tmp_path: Path):
    workflow = build_workflow(tmp_path / "standards.json", Settings())

    assert workflow.graph is not None

