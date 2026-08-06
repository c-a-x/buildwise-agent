"""隐患语音广播（网络音响/PA webhook 预留）。

实时检测到高危隐患时，向后端配置的 `BROADCAST_WEBHOOK_URL`（例如网络音响、
IP 广播的 HTTP 服务）发 fire-and-forget 通知，同时推送文字与（TTS 配置成功时的）
音频。任何异常只静默吞掉，绝不阻塞实时检测主链路；未配置 webhook 时直接返回。
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import Settings
from app.core.exceptions import AppError
from app.providers.factory import build_tts_provider

_MAX_NAMES = 3  # 播报文案最多取前 3 个隐患名，避免过长


def build_broadcast_message(hazards: list[dict[str, Any]]) -> str:
    """从隐患列表生成中文播报文案；无有效隐患名返回空串。"""
    seen: set[str] = set()
    names: list[str] = []
    for item in hazards:
        name = str(item.get("hazard_name", "")).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
        if len(names) >= _MAX_NAMES:
            break
    if not names:
        return ""
    return f"警告！检测到{'、'.join(names)}，请立即整改。"


def _build_text_payload(message: str, settings: Settings) -> dict[str, Any]:
    """按给定文案构建广播 payload（文字 + 可选 TTS 音频）。合成失败降级为只推文字。"""
    payload: dict[str, Any] = {
        "source": "buildwise-broadcast",
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "message": message,
        "tts": {"provider": None, "available": False, "is_simulated": False},
    }
    try:
        provider = build_tts_provider(settings)
    except AppError:
        return payload
    if provider is None:
        return payload
    try:
        audio = provider.synthesize(message)
    except AppError:
        return payload  # 合成失败降级：只推文字
    payload["audio_base64"] = base64.b64encode(audio).decode("ascii")
    payload["audio_format"] = "mp3"
    payload["tts"] = {
        "provider": provider.name,
        "available": True,
        "is_simulated": provider.is_simulated,
    }
    return payload


def _build_payload(hazards: list[dict[str, Any]], settings: Settings) -> dict[str, Any]:
    payload = _build_text_payload(build_broadcast_message(hazards), settings)
    payload["hazards"] = hazards
    return payload


def _dispatch(payload: dict[str, Any], webhook_url: str) -> bool:
    """POST 到 webhook；失败静默返回 False。"""
    try:
        with httpx.Client(timeout=8.0) as client:
            response = client.post(webhook_url, json=payload)
        return response.status_code < 400
    except (httpx.HTTPError, OSError, ValueError):
        return False


def broadcast_voice_alert(hazards: list[dict[str, Any]], settings: Settings) -> None:
    """向网络音响/PA webhook 上报当前高危隐患（文字 + 可选音频）。失败静默。"""
    if not settings.broadcast_webhook_url:
        return
    payload = _build_payload(hazards, settings)
    if not payload["message"]:
        return
    _dispatch(payload, settings.broadcast_webhook_url)


def broadcast_text_alert(message: str, settings: Settings) -> None:
    """向网络音响/PA webhook 上报一条自定义文字播报（如高温红色预警）。失败静默。"""
    if not settings.broadcast_webhook_url:
        return
    if not message.strip():
        return
    payload = _build_text_payload(message, settings)
    _dispatch(payload, settings.broadcast_webhook_url)


def send_test_broadcast(settings: Settings) -> dict[str, Any]:
    """手动触发一次测试广播并返回结果，供 /broadcast-test 端点反馈。"""
    hazards = [{"hazard_type": "no_helmet", "hazard_name": "未佩戴安全帽", "risk_level": "high"}]
    payload = _build_payload(hazards, settings)
    if not settings.broadcast_webhook_url:
        return {
            "delivered": False,
            "message": payload["message"],
            "tts": payload["tts"],
            "reason": "未配置 BROADCAST_WEBHOOK_URL",
        }
    delivered = _dispatch(payload, settings.broadcast_webhook_url)
    return {
        "delivered": delivered,
        "message": payload["message"],
        "tts": payload["tts"],
        "reason": None if delivered else "webhook 未返回成功（检查设备地址/网络）",
    }
