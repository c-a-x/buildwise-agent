from __future__ import annotations

from app.core.config import Settings
from app.core.exceptions import AppError
from app.providers.retrieval.base import RetrievalProvider
from app.providers.retrieval.chroma import ChromaRetrievalProvider
from app.providers.retrieval.local_keyword import LocalKeywordRetrievalProvider
from app.providers.speech.base import SpeechTranscriptionProvider
from app.providers.speech.openai_compatible import OpenAICompatibleSpeechProvider
from app.providers.text.base import TextProvider
from app.providers.text.openai_compatible import OpenAICompatibleTextProvider
from app.providers.text.template import TemplateTextProvider
from app.providers.tts.base import SpeechSynthesisProvider
from app.providers.tts.edge_tts import EdgeTTSSpeechProvider
from app.providers.tts.mock import MockTTSSpeechProvider
from app.providers.vision.base import VisionProvider
from app.providers.vision.hybrid import SafetyHybridVisionProvider
from app.providers.vision.mock import MockVisionProvider
from app.providers.vision.quality_hybrid import QualityHybridVisionProvider
from app.providers.vision.ultralytics import UltralyticsVisionProvider
from app.providers.weather.base import WeatherProvider
from app.providers.weather.openweather import OpenWeatherProvider
from app.providers.weather.qweather import QWeatherProvider


def build_vision_provider(settings: Settings) -> VisionProvider:
    if settings.vision_provider == "mock":
        return MockVisionProvider()
    if settings.vision_provider == "ultralytics":
        if not settings.vision_model_path:
            raise AppError("请配置 VISION_MODEL_PATH", "PROVIDER_NOT_CONFIGURED", 500)
        return UltralyticsVisionProvider(settings.vision_model_path)
    if settings.vision_provider == "safety_hybrid":
        return SafetyHybridVisionProvider(settings)
    if settings.vision_provider == "quality_hybrid":
        return QualityHybridVisionProvider(settings)
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


def build_speech_provider(settings: Settings) -> SpeechTranscriptionProvider:
    if settings.speech_provider == "openai_compatible":
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
            raise AppError(f"SPEECH_PROVIDER=openai_compatible 请配置 {', '.join(missing)}", "PROVIDER_NOT_CONFIGURED", 500)
        return OpenAICompatibleSpeechProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
        )
    raise AppError(
        "未配置语音转写 Provider（SPEECH_PROVIDER=off，离线时前端使用浏览器 Web Speech 识别）",
        "PROVIDER_NOT_CONFIGURED",
        500,
    )


def build_tts_provider(settings: Settings) -> SpeechSynthesisProvider | None:
    """构建语音合成 Provider；未配置（off）时返回 None，广播仍走文字通道。

    与 build_speech_provider 不同：TTS 是可选增强，不配置/失败都不抛错，
    由广播服务降级为只推文字（设备自行 TTS）。
    """
    if settings.tts_provider == "edge_tts":
        return EdgeTTSSpeechProvider(voice=settings.tts_voice)
    if settings.tts_provider == "mock":
        return MockTTSSpeechProvider()
    return None


def build_weather_provider(settings: Settings) -> WeatherProvider | None:
    """构建实时天气 Provider；未配置（off 或缺 WEATHER_API_KEY）时返回 None。

    与 TTS 语义一致：天气是可选增强，工友关怀未配置时回退手动输入，不抛错。
    """
    if settings.weather_provider == "openweather":
        if not settings.weather_api_key:
            return None
        return OpenWeatherProvider(settings.weather_api_base_url, settings.weather_api_key)
    if settings.weather_provider == "qweather":
        if not settings.weather_api_key:
            return None
        return QWeatherProvider(
            settings.weather_geo_api_base_url,
            settings.weather_api_base_url,
            settings.weather_api_key,
            settings.weather_auth_type,
        )
    return None
