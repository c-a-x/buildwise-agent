from __future__ import annotations

from pydantic import BaseModel, Field


class HardwareTelemetryIn(BaseModel):
    device_id: str = Field(default="esp32-site-01", max_length=64)
    temperature_c: float = Field(ge=-40, le=80)
    humidity_pct: float = Field(ge=0, le=100)
    heat_alarm: bool = False
    buzzer_on: bool = False
    led_state: str | None = Field(default=None, max_length=32)
    ip_address: str | None = Field(default=None, max_length=45)
    rssi_dbm: int | None = Field(default=None, ge=-120, le=20)
    uptime_ms: int | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=160)


class HardwareTelemetryRead(HardwareTelemetryIn):
    observed_at: str
    received_at: str
    is_fresh: bool = True
