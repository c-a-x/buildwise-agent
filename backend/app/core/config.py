from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - optional during packaging
    pass


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


def _path_from_env(value: str, default: str) -> Path:
    candidate = Path(value or default)
    return (candidate if candidate.is_absolute() else BACKEND_DIR / candidate).resolve()


def _normalize_database_url(value: str) -> str:
    """Resolve relative SQLite files from the backend directory, not cwd."""
    database_url = value.strip()
    if not database_url.startswith("sqlite:///"):
        return database_url
    database_path = database_url.removeprefix("sqlite:///")
    if database_path == ":memory:":
        return database_url
    candidate = Path(database_path)
    if not candidate.is_absolute():
        candidate = (BACKEND_DIR / candidate).resolve()
    return f"sqlite:///{candidate.as_posix()}"


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "BuildWise AI Agent")
    app_env: str = os.getenv("APP_ENV", "development")
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"
    api_prefix: str = os.getenv("API_PREFIX", "/api/v1")
    secret_key: str = os.getenv("SECRET_KEY", "buildwise-local-development-key")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
    database_url: str = _normalize_database_url(os.getenv("DATABASE_URL", "sqlite:///./storage/buildwise.db"))
    upload_dir: Path = _path_from_env(os.getenv("UPLOAD_DIR", "storage/uploads"), "storage/uploads")
    annotated_dir: Path = _path_from_env(os.getenv("ANNOTATED_DIR", "storage/annotated"), "storage/annotated")
    reports_dir: Path = _path_from_env(os.getenv("REPORTS_DIR", "storage/reports"), "storage/reports")
    chroma_dir: Path = _path_from_env(os.getenv("CHROMA_DIR", "storage/chroma"), "storage/chroma")
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "10"))
    vision_provider: str = os.getenv("VISION_PROVIDER", "mock")
    vision_model_path: str = os.getenv("VISION_MODEL_PATH", "")
    yolo_model_path: Path = _path_from_env(
        os.getenv("YOLO_MODEL_PATH", "storage/models/yolov8n.pt"),
        "storage/models/yolov8n.pt",
    )
    yolo_conf_threshold: float = float(os.getenv("YOLO_CONF_THRESHOLD", "0.5"))
    quality_model_path: Path = _path_from_env(
        os.getenv("QUALITY_MODEL_PATH", "storage/models/yolov8n-5cls-mbdd.pt"),
        "storage/models/yolov8n-5cls-mbdd.pt",
    )
    quality_conf_threshold: float = float(os.getenv("QUALITY_CONF_THRESHOLD", "0.45"))
    vision_llm_provider: str = os.getenv("VISION_LLM_PROVIDER", "off")  # claude_cli | doubao | zhipu | off
    vision_llm_claude_cmd: str = os.getenv("VISION_LLM_CLAUDE_CMD", "claude")
    vision_llm_timeout: int = int(os.getenv("VISION_LLM_TIMEOUT", "300"))
    # 视觉 LLM（OpenAI 兼容 HTTP 调用：doubao / zhipu）的独立配置，兜底取 LLM_*，
    # 避免与纯文本 LLM（如 DeepSeek）共用同组 key/model 时冲突
    vision_llm_base_url: str = os.getenv("VISION_LLM_BASE_URL", os.getenv("LLM_BASE_URL", ""))
    vision_llm_api_key: str = os.getenv("VISION_LLM_API_KEY", os.getenv("LLM_API_KEY", ""))
    vision_llm_model: str = os.getenv("VISION_LLM_MODEL", os.getenv("LLM_MODEL", ""))
    alert_webhook_url: str = os.getenv("ALERT_WEBHOOK_URL", "")  # ESP32 硬报警地址，默认空禁用
    tts_provider: str = os.getenv("TTS_PROVIDER", "off")  # off | edge_tts | mock
    tts_voice: str = os.getenv("TTS_VOICE", "zh-CN-XiaoxiaoNeural")
    broadcast_webhook_url: str = os.getenv("BROADCAST_WEBHOOK_URL", "")  # 网络音响/PA 广播地址，默认空禁用
    retrieval_provider: str = os.getenv("RETRIEVAL_PROVIDER", "local_keyword")
    chroma_min_score: float = float(os.getenv("CHROMA_MIN_SCORE", "0.42"))
    text_provider: str = os.getenv("TEXT_PROVIDER", "template")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "")
    speech_provider: str = os.getenv("SPEECH_PROVIDER", "off")  # off | openai_compatible
    knowledge_json_path: Path = _path_from_env(
        os.getenv("KNOWLEDGE_JSON_PATH", "../data_demo/standards/safety_standards.json"),
        "../data_demo/standards/safety_standards.json",
    )
    quality_knowledge_json_path: Path = _path_from_env(
        os.getenv("QUALITY_KNOWLEDGE_JSON_PATH", "../data_demo/standards/quality_standards.json"),
        "../data_demo/standards/quality_standards.json",
    )
    green_factors_path: Path = _path_from_env(
        os.getenv("GREEN_FACTORS_PATH", "../data_demo/green/factors.json"),
        "../data_demo/green/factors.json",
    )
    green_reference_path: Path = _path_from_env(
        os.getenv("GREEN_REFERENCE_PATH", "../data_demo/green/reference.json"),
        "../data_demo/green/reference.json",
    )
    wellbeing_rules_path: Path = _path_from_env(
        os.getenv("WELLBEING_RULES_PATH", "../data_demo/wellbeing/rules.json"),
        "../data_demo/wellbeing/rules.json",
    )
    weather_provider: str = os.getenv("WEATHER_PROVIDER", "off")  # off | openweather | qweather
    weather_api_base_url: str = os.getenv("WEATHER_API_BASE_URL", "https://api.openweathermap.org/data/2.5")
    weather_api_key: str = os.getenv("WEATHER_API_KEY", "")
    weather_city: str = os.getenv("WEATHER_CITY", "")
    care_schedule_enabled: bool = os.getenv("CARE_SCHEDULE_ENABLED", "false").lower() == "true"  # 定时关怀开关
    care_schedule_time: str = os.getenv("CARE_SCHEDULE_TIME", "08:00")  # 每日自动评估时间 HH:MM
    care_schedule_city: str = os.getenv("CARE_SCHEDULE_CITY", "")  # 定时关怀城市，缺省取 WEATHER_CITY
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    )

    @property
    def storage_dir(self) -> Path:
        return self.upload_dir.parent


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
