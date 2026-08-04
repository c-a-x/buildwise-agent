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
    return candidate if candidate.is_absolute() else BACKEND_DIR / candidate


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
    retrieval_provider: str = os.getenv("RETRIEVAL_PROVIDER", "local_keyword")
    text_provider: str = os.getenv("TEXT_PROVIDER", "template")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "")
    knowledge_json_path: Path = _path_from_env(
        os.getenv("KNOWLEDGE_JSON_PATH", "../data_demo/standards/safety_standards.json"),
        "../data_demo/standards/safety_standards.json",
    )
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
