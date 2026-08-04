from __future__ import annotations

from app.core.config import Settings
from app.core.exceptions import AppError
from app.providers.retrieval.base import RetrievalProvider
from app.providers.retrieval.chroma import ChromaRetrievalProvider
from app.providers.retrieval.local_keyword import LocalKeywordRetrievalProvider
from app.providers.text.base import TextProvider
from app.providers.text.openai_compatible import OpenAICompatibleTextProvider
from app.providers.text.template import TemplateTextProvider
from app.providers.vision.base import VisionProvider
from app.providers.vision.hybrid import SafetyHybridVisionProvider
from app.providers.vision.mock import MockVisionProvider
from app.providers.vision.ultralytics import UltralyticsVisionProvider


def build_vision_provider(settings: Settings) -> VisionProvider:
    if settings.vision_provider == "mock":
        return MockVisionProvider()
    if settings.vision_provider == "ultralytics":
        if not settings.vision_model_path:
            raise AppError("请配置 VISION_MODEL_PATH", "PROVIDER_NOT_CONFIGURED", 500)
        return UltralyticsVisionProvider(settings.vision_model_path)
    if settings.vision_provider == "safety_hybrid":
        return SafetyHybridVisionProvider(settings)
    raise AppError("不支持的视觉 Provider", "PROVIDER_NOT_SUPPORTED", 500)


def build_retrieval_provider(settings: Settings) -> RetrievalProvider:
    if settings.retrieval_provider == "local_keyword":
        return LocalKeywordRetrievalProvider(settings.knowledge_json_path)
    if settings.retrieval_provider == "chroma":
        try:
            return ChromaRetrievalProvider(settings.chroma_dir, min_score=settings.chroma_min_score)
        except RuntimeError as exc:
            raise AppError(str(exc), "PROVIDER_NOT_CONFIGURED", 500) from exc
    raise AppError("不支持的检索 Provider", "PROVIDER_NOT_SUPPORTED", 500)


def build_text_provider(settings: Settings) -> TextProvider:
    if settings.text_provider == "template":
        return TemplateTextProvider()
    if settings.text_provider == "openai_compatible":
        missing = [
            name
            for name, value in (
                ("LLM_BASE_URL", settings.llm_base_url),
                ("LLM_API_KEY", settings.llm_api_key),
                ("LLM_MODEL", settings.llm_model),
            )
            if not value
        ]
        if missing:
            raise AppError(f"TEXT_PROVIDER=openai_compatible 请配置 {', '.join(missing)}", "PROVIDER_NOT_CONFIGURED", 500)
        return OpenAICompatibleTextProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
        )
    raise AppError("不支持的文本 Provider", "PROVIDER_NOT_SUPPORTED", 500)
