from __future__ import annotations

import hashlib
from pathlib import Path

from app.core.exceptions import AppError
from app.utils.ids import new_id


ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def validate_upload(content_type: str | None, size_bytes: int, max_mb: int) -> str:
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise AppError("仅支持 JPEG、PNG 或 WEBP 图片", "UPLOAD_INVALID_TYPE", 400)
    if size_bytes > max_mb * 1024 * 1024:
        raise AppError(f"图片不能超过 {max_mb} MB", "UPLOAD_TOO_LARGE", 413)
    return ALLOWED_IMAGE_TYPES[content_type]


def save_upload(content: bytes, content_type: str, directory: Path, max_mb: int) -> tuple[str, str, int]:
    suffix = validate_upload(content_type, len(content), max_mb)
    stored_name = f"{new_id('IMG')}{suffix}"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / stored_name
    path.write_bytes(content)
    return stored_name, hashlib.sha256(content).hexdigest(), len(content)
