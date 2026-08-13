from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.config import Settings, settings as default_settings
from app.schemas.hardware import HardwareTelemetryIn, HardwareTelemetryRead


class HardwareTelemetryService:
    """Store the latest ESP32 site sensor reading on disk."""

    def __init__(self, runtime_settings: Settings | None = None) -> None:
        self.settings = runtime_settings or default_settings
        self.path: Path = self.settings.hardware_telemetry_path

    def save(self, payload: HardwareTelemetryIn) -> HardwareTelemetryRead:
        now = datetime.now(timezone.utc).isoformat()
        data = payload.model_dump()
        data["observed_at"] = now
        data["received_at"] = now
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(self.path)
        return self._with_freshness(data)

    def latest(self, *, fresh_only: bool = False) -> HardwareTelemetryRead | None:
        if not self.path.exists():
            return None
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return None
        reading = self._with_freshness(data)
        if fresh_only and not reading.is_fresh:
            return None
        return reading

    def _with_freshness(self, data: dict[str, object]) -> HardwareTelemetryRead:
        received_at = self._parse_time(str(data.get("received_at") or ""))
        is_fresh = datetime.now(timezone.utc) - received_at <= timedelta(seconds=self.settings.hardware_fresh_seconds)
        return HardwareTelemetryRead(**data, is_fresh=is_fresh)

    @staticmethod
    def _parse_time(value: str) -> datetime:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.fromtimestamp(0, timezone.utc)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
