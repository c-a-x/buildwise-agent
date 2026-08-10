"""Offline provider readiness preflight.

The command only inspects settings, import metadata, and local resource paths.
It never opens the database, performs model inference, rebuilds an index, or
contacts an external service.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.config import Settings, settings  # noqa: E402
from app.services.runtime_service import CapabilityStatus, ProviderCapabilities, provider_capabilities  # noqa: E402


def collect_capabilities(runtime_settings: Settings = settings) -> ProviderCapabilities:
    return provider_capabilities(runtime_settings)


def _status_label(status: CapabilityStatus) -> str:
    return {
        "available": "AVAILABLE",
        "configured": "CONFIGURED",
        "simulated": "SIMULATED",
        "not_configured": "WARNING",
        "unavailable": "UNAVAILABLE",
    }.get(status, status.upper())


def render_report(capabilities: ProviderCapabilities) -> str:
    lines = ["Provider 预检（只读，不执行模型推理或访问外网）"]
    for capability in capabilities.values():
        lines.append(
            f"[{_status_label(capability['status'])}] {capability['name']} "
            f"provider={capability['provider']} "
            f"is_simulated={str(capability['is_simulated']).lower()}"
        )
        lines.append(f"  原因：{capability['reason']}")
        lines.append(f"  下一步：{capability['next_step']}")
    return "\n".join(lines)


def run(runtime_settings: Settings = settings) -> int:
    capabilities = collect_capabilities(runtime_settings)
    print(render_report(capabilities))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
