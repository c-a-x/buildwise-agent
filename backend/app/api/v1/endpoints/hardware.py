from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.response import ok
from app.core.config import settings
from app.schemas.hardware import HardwareTelemetryIn
from app.services.hardware_service import HardwareTelemetryService


router = APIRouter(prefix="/hardware", tags=["hardware"])


@router.post("/telemetry")
def receive_telemetry(payload: HardwareTelemetryIn, http_request: Request):
    """Receive one ESP32 sensor reading from the local network."""
    data = HardwareTelemetryService(settings).save(payload)
    return ok(data.model_dump(mode="json"), http_request, "hardware telemetry received")


@router.get("/telemetry/latest")
def latest_telemetry(http_request: Request):
    data = HardwareTelemetryService(settings).latest()
    return ok(data.model_dump(mode="json") if data else None, http_request)
