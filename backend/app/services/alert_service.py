"""隐患硬报警通知（ESP32 蜂鸣器 webhook 预留）。

实时检测到高危隐患（或高温警告）时，向后端配置的 `ALERT_WEBHOOK_URL`（例如
ESP32 上运行的 HTTP 服务）发 fire-and-forget 通知，由其驱动 GPIO 蜂鸣器。
任何异常只静默吞掉，绝不阻塞实时检测主链路；未配置 webhook 时直接返回。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx


def notify_hard_alert(hazards: list[dict[str, Any]], webhook_url: str, message: str | None = None) -> None:
    """向 ESP32 webhook 上报硬报警。失败静默。

    - 安全侧：传 `hazards`（高危隐患），payload 带 `hazards` 字段；
    - 高温关怀侧：无隐患列表，传 `message`（如"高温红色预警…"）+ 空 `hazards`，
      ESP32 固件可按有无 `message` 分支驱动蜂鸣器（响铃节奏/次数可区分场景）。
    """
    if not webhook_url:
        return
    payload: dict[str, Any] = {
        "source": "buildwise-realtime",
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "hazards": hazards,
    }
    if message:
        payload["message"] = message
    try:
        with httpx.Client(timeout=3.0) as client:
            client.post(webhook_url, json=payload)
    except (httpx.HTTPError, OSError, ValueError):
        pass
