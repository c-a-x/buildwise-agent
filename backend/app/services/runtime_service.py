from __future__ import annotations

import sqlite3
from importlib.util import find_spec
from pathlib import Path
from typing import Literal, TypedDict

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR, Settings, settings


CapabilityStatus = Literal["available", "configured", "simulated", "not_configured", "unavailable"]
CapabilityKey = Literal["vision", "retrieval", "text", "speech", "weather", "tts", "broadcast"]


class ProviderCapability(TypedDict):
    key: CapabilityKey
    name: str
    provider: str
    status: CapabilityStatus
    is_simulated: bool
    reason: str
    next_step: str


ProviderCapabilities = dict[CapabilityKey, ProviderCapability]


def _module_available(module_name: str) -> bool:
    try:
        return find_spec(module_name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def _resolved_file(value: str | Path) -> Path:
    candidate = Path(value)
    return (candidate if candidate.is_absolute() else BACKEND_DIR / candidate).resolve()


def _chroma_persistence_ready(index_dir: Path) -> bool:
    marker = index_dir / "chroma.sqlite3"
    try:
        if not marker.is_file() or marker.read_bytes()[:16] != b"SQLite format 3\x00":
            return False
        connection = sqlite3.connect(f"file:{marker}?mode=ro", uri=True)
        try:
            tables = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN ('collections', 'embeddings')"
            ).fetchall()
            return {str(row[0]) for row in tables} == {"collections", "embeddings"}
        finally:
            connection.close()
    except (sqlite3.Error, OSError):
        return False


def _capability(
    key: CapabilityKey,
    name: str,
    provider: str,
    status: CapabilityStatus,
    is_simulated: bool,
    reason: str,
    next_step: str,
) -> ProviderCapability:
    return {
        "key": key,
        "name": name,
        "provider": provider,
        "status": status,
        "is_simulated": is_simulated,
        "reason": reason,
        "next_step": next_step,
    }


def _missing_llm_fields(runtime_settings: Settings) -> list[str]:
    return [
        name
        for name, value in (
            ("LLM_BASE_URL", runtime_settings.llm_base_url),
            ("LLM_API_KEY", runtime_settings.llm_api_key),
            ("LLM_MODEL", runtime_settings.llm_model),
        )
        if not value
    ]


def _vision_capability(runtime_settings: Settings) -> ProviderCapability:
    provider = runtime_settings.vision_provider
    if provider == "mock":
        return _capability(
            "vision",
            "视觉识别",
            provider,
            "simulated",
            True,
            "当前使用离线模拟视觉，不加载模型也不访问外网。",
            "配置 VISION_PROVIDER=safety_hybrid 或 ultralytics，并提供依赖与模型权重。",
        )

    if provider == "ultralytics":
        if not runtime_settings.vision_model_path:
            return _capability(
                "vision",
                "视觉识别",
                provider,
                "not_configured",
                False,
                "真实 Ultralytics Provider 未配置 VISION_MODEL_PATH。",
                "设置 VISION_MODEL_PATH 指向可用的 YOLO 权重文件。",
            )
        model_path = _resolved_file(runtime_settings.vision_model_path)
        missing: list[str] = []
        if not _module_available("ultralytics"):
            missing.append("未安装 ultralytics")
        if not model_path.is_file():
            missing.append(f"模型文件不存在：{model_path}")
        if missing:
            return _capability(
                "vision",
                "视觉识别",
                provider,
                "unavailable",
                False,
                "；".join(missing),
                "安装 backend[vision] 依赖并准备 VISION_MODEL_PATH 指向的权重。",
            )
        return _capability(
            "vision",
            "视觉识别",
            provider,
            "configured",
            False,
            "Ultralytics 依赖与模型权重已配置；健康检查不会执行推理。",
            "运行真实图片 smoke test 验证模型输出。",
        )

    if provider in {"safety_hybrid", "quality_hybrid"}:
        model_path = (
            runtime_settings.quality_model_path
            if provider == "quality_hybrid"
            else runtime_settings.yolo_model_path
        )
        missing: list[str] = []
        if not _module_available("ultralytics"):
            missing.append("未安装 ultralytics")
        if not model_path.is_file():
            missing.append(f"模型文件不存在：{model_path}")
        if missing:
            return _capability(
                "vision",
                "视觉识别",
                provider,
                "simulated",
                True,
                "；".join(missing) + "；混合 Provider 将回退离线模拟结果。",
                "安装 backend[vision] 依赖并准备对应模型后，再用真实图片 smoke test 验证。",
            )
        return _capability(
            "vision",
            "视觉识别",
            provider,
            "configured",
            False,
            "混合视觉 Provider 的依赖与模型权重已配置；健康检查不会执行推理。",
            "运行真实图片 smoke test 验证 YOLO 输出和降级路径。",
        )

    return _capability(
        "vision",
        "视觉识别",
        provider,
        "unavailable",
        False,
        f"不支持的视觉 Provider：{provider}。",
        "将 VISION_PROVIDER 改为 mock、safety_hybrid、quality_hybrid 或 ultralytics。",
    )


def _retrieval_capability(runtime_settings: Settings) -> ProviderCapability:
    provider = runtime_settings.retrieval_provider
    if provider == "local_keyword":
        return _capability(
            "retrieval",
            "规范检索",
            provider,
            "available",
            False,
            "使用本地规范 JSON 的关键词检索，完全离线且不会伪造未命中条款。",
            "可选设置 RETRIEVAL_PROVIDER=chroma 并运行知识库重建。",
        )
    if provider == "chroma":
        if not _module_available("chromadb"):
            return _capability(
                "retrieval",
                "规范检索",
                provider,
                "unavailable",
                False,
                "未安装 chromadb，无法读取持久化向量索引。",
                "安装 backend 的 Chroma 依赖后运行知识库重建。",
            )
        if not _chroma_persistence_ready(runtime_settings.chroma_dir):
            return _capability(
                "retrieval",
                "规范检索",
                provider,
                "not_configured",
                False,
                "Chroma 依赖已安装，但不存在非空的 chroma.sqlite3 持久化索引标记。",
                "运行 POST /api/v1/knowledge/reindex 重建规范索引。",
            )
        return _capability(
            "retrieval",
            "规范检索",
            provider,
            "available",
            False,
            "Chroma 持久化 chroma.sqlite3 标记已存在；健康检查不会创建客户端、查询或写入索引。",
            "用知识库索引状态接口确认条款数量。",
        )
    return _capability(
        "retrieval",
        "规范检索",
        provider,
        "unavailable",
        False,
        f"不支持的检索 Provider：{provider}。",
        "将 RETRIEVAL_PROVIDER 改为 local_keyword 或 chroma。",
    )


def _text_capability(runtime_settings: Settings) -> ProviderCapability:
    provider = runtime_settings.text_provider
    if provider == "template":
        return _capability(
            "text",
            "文本生成",
            provider,
            "simulated",
            True,
            "当前使用离线模板生成，数字和事实不会交给外部模型改写。",
            "如需真实生成，配置 LLM_BASE_URL、LLM_API_KEY 和 LLM_MODEL。",
        )
    if provider == "openai_compatible":
        missing = _missing_llm_fields(runtime_settings)
        if missing:
            return _capability(
                "text",
                "文本生成",
                provider,
                "not_configured",
                False,
                f"OpenAI 兼容文本 Provider 缺少配置：{', '.join(missing)}。",
                "补齐上述环境变量后运行真实文本请求 smoke test。",
            )
        return _capability(
            "text",
            "文本生成",
            provider,
            "configured",
            False,
            "OpenAI 兼容文本 Provider 配置完整；健康检查不会访问外网。",
            "运行真实请求 smoke test 验证地址、密钥和模型。",
        )
    return _capability("text", "文本生成", provider, "unavailable", False, f"不支持的文本 Provider：{provider}。", "将 TEXT_PROVIDER 改为 template 或 openai_compatible。")


def _speech_capability(runtime_settings: Settings) -> ProviderCapability:
    provider = runtime_settings.speech_provider
    if provider == "off":
        return _capability("speech", "语音转写", provider, "not_configured", False, "后端语音转写未配置，前端可使用浏览器 Web Speech 离线识别。", "需要服务端 ASR 时配置 SPEECH_PROVIDER=openai_compatible 及三个 LLM 配置。")
    if provider == "openai_compatible":
        missing = _missing_llm_fields(runtime_settings)
        if missing:
            return _capability("speech", "语音转写", provider, "not_configured", False, f"语音转写缺少配置：{', '.join(missing)}。", "补齐 LLM_BASE_URL、LLM_API_KEY 和 LLM_MODEL 后运行 ASR smoke test。")
        return _capability("speech", "语音转写", provider, "configured", False, "OpenAI 兼容 ASR 配置完整；健康检查不会上传音频。", "运行真实音频 smoke test 验证转写服务。")
    return _capability("speech", "语音转写", provider, "unavailable", False, f"不支持的语音 Provider：{provider}。", "将 SPEECH_PROVIDER 改为 off 或 openai_compatible。")


def _tts_capability(runtime_settings: Settings) -> ProviderCapability:
    provider = runtime_settings.tts_provider
    if provider == "off":
        return _capability("tts", "语音合成", provider, "not_configured", False, "后端 TTS 未配置，广播服务会保留文字通道。", "需要服务端音频时配置 TTS_PROVIDER=edge_tts 并安装 edge-tts。")
    if provider == "mock":
        return _capability("tts", "语音合成", provider, "simulated", True, "当前使用离线 TTS 模拟 Provider，仅用于演示。", "需要真实音频时改为 edge_tts 并确认网络与语音服务可用。")
    if provider == "edge_tts":
        if not _module_available("edge_tts"):
            return _capability("tts", "语音合成", provider, "unavailable", False, "已选择 edge_tts，但未安装 edge-tts 依赖。", "执行 pip install -e \"backend[tts]\"，再运行真实合成 smoke test。")
        return _capability("tts", "语音合成", provider, "configured", False, "edge-tts 依赖已安装；健康检查不会发起合成请求。", "运行真实合成 smoke test 验证网络和语音服务。")
    return _capability("tts", "语音合成", provider, "unavailable", False, f"不支持的 TTS Provider：{provider}。", "将 TTS_PROVIDER 改为 off、mock 或 edge_tts。")


def _weather_capability(runtime_settings: Settings) -> ProviderCapability:
    provider = runtime_settings.weather_provider
    if provider == "off":
        return _capability("weather", "实时天气", provider, "not_configured", False, "天气 Provider 未配置，工友关怀仍支持手动输入。", "配置 WEATHER_PROVIDER=openweather、WEATHER_API_KEY 和 WEATHER_CITY。")
    if provider == "openweather":
        missing = [name for name, value in (("WEATHER_API_KEY", runtime_settings.weather_api_key), ("WEATHER_CITY", runtime_settings.weather_city)) if not value]
        if missing:
            return _capability("weather", "实时天气", provider, "not_configured", False, f"实时天气 OpenWeather 缺少配置：{', '.join(missing)}。", "补齐天气密钥与城市后运行真实天气 smoke test。")
        return _capability("weather", "实时天气", provider, "configured", False, "OpenWeather 配置完整；健康检查不会请求外部天气接口。", "运行真实天气 smoke test 验证网络和城市参数。")
    if provider == "qweather":
        missing = [name for name, value in (("WEATHER_API_KEY", runtime_settings.weather_api_key), ("WEATHER_CITY", runtime_settings.weather_city)) if not value]
        if missing:
            return _capability("weather", "实时天气", provider, "not_configured", False, f"实时天气和风天气缺少配置：{', '.join(missing)}。", "补齐天气密钥与城市后运行真实天气 smoke test。")
        return _capability("weather", "实时天气", provider, "configured", False, "和风天气配置完整；健康检查不会请求外部天气接口。", "运行真实天气 smoke test 验证网络和城市参数。")
    return _capability("weather", "实时天气", provider, "unavailable", False, f"不支持的天气 Provider：{provider}。", "将 WEATHER_PROVIDER 改为 off、openweather 或 qweather。")


def _broadcast_capability(runtime_settings: Settings) -> ProviderCapability:
    if not runtime_settings.broadcast_webhook_url:
        return _capability("broadcast", "硬件广播", "off", "not_configured", False, "广播 webhook 未配置，高危提醒只保留应用内文字与浏览器语音。", "配置 BROADCAST_WEBHOOK_URL 后运行设备广播 smoke test。")
    return _capability("broadcast", "硬件广播", "webhook", "configured", False, "广播 webhook 已配置；健康检查不会发送测试消息。", "使用广播测试接口确认设备地址和网络连通性。")


class RuntimeService:
    def __init__(self, db: Session):
        self.db = db

    def database_status(self) -> dict[str, object]:
        bind = self.db.get_bind()
        dialect = bind.dialect.name
        database_url = bind.url
        persistent = not (dialect == "sqlite" and database_url.database in (None, "", ":memory:"))
        try:
            self.db.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return {"status": "unavailable", "dialect": dialect, "persistent": persistent}
        return {"status": "connected", "dialect": dialect, "persistent": persistent}


def provider_capabilities(runtime_settings: Settings = settings) -> ProviderCapabilities:
    """Return cheap, read-only provider readiness information.

    This deliberately checks configuration, local files, and import metadata only.
    It never loads a model, queries Chroma, sends network traffic, or writes data.
    """
    return {
        "vision": _vision_capability(runtime_settings),
        "retrieval": _retrieval_capability(runtime_settings),
        "text": _text_capability(runtime_settings),
        "speech": _speech_capability(runtime_settings),
        "weather": _weather_capability(runtime_settings),
        "tts": _tts_capability(runtime_settings),
        "broadcast": _broadcast_capability(runtime_settings),
    }


def _weather_capability(runtime_settings: Settings) -> ProviderCapability:
    provider = runtime_settings.weather_provider
    if provider == "off":
        return _capability(
            "weather",
            "实时天气",
            provider,
            "not_configured",
            False,
            "天气 Provider 未配置，工友关怀仍支持手动输入。",
            "配置 WEATHER_PROVIDER=openweather 或 qweather、WEATHER_API_KEY 和 WEATHER_CITY。",
        )
    if provider in {"openweather", "qweather"}:
        missing = [
            name
            for name, value in (
                ("WEATHER_API_KEY", runtime_settings.weather_api_key),
                ("WEATHER_CITY", runtime_settings.weather_city),
            )
            if not value
        ]
        if missing:
            label = "OpenWeather" if provider == "openweather" else "QWeather"
            return _capability(
                "weather",
                "实时天气",
                provider,
                "not_configured",
                False,
                f"实时天气 {label} 缺少配置：{', '.join(missing)}。",
                "补齐天气密钥与城市后运行真实天气 smoke test。",
            )
        label = "OpenWeather" if provider == "openweather" else "QWeather"
        return _capability(
            "weather",
            "实时天气",
            provider,
            "configured",
            False,
            f"{label} 配置完整；健康检查不会请求外部天气接口。",
            "运行真实天气 smoke test 验证网络和城市参数。",
        )
    return _capability(
        "weather",
        "实时天气",
        provider,
        "unavailable",
        False,
        f"不支持的天气 Provider：{provider}。",
        "将 WEATHER_PROVIDER 改为 off、openweather 或 qweather。",
    )
