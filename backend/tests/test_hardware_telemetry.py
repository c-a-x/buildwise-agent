from __future__ import annotations

from dataclasses import replace

from app.core.config import settings
from app.schemas.hardware import HardwareTelemetryIn
from app.services.hardware_service import HardwareTelemetryService


def test_hardware_telemetry_roundtrip(tmp_path):
    runtime_settings = replace(
        settings,
        hardware_telemetry_path=tmp_path / "latest_telemetry.json",
        weather_provider="off",
    )
    service = HardwareTelemetryService(runtime_settings)
    saved = service.save(
        HardwareTelemetryIn(
            device_id="esp32-test",
            temperature_c=36.8,
            humidity_pct=67,
            heat_alarm=True,
            buzzer_on=True,
            led_state="red_alarm",
            ip_address="192.168.1.50",
            rssi_dbm=-48,
            uptime_ms=12345,
        )
    )

    latest = service.latest()

    assert saved.is_fresh is True
    assert latest is not None
    assert latest.device_id == "esp32-test"
    assert latest.temperature_c == 36.8
    assert latest.humidity_pct == 67
    assert latest.heat_alarm is True
    assert latest.buzzer_on is True
    assert latest.led_state == "red_alarm"
    assert latest.is_fresh is True
