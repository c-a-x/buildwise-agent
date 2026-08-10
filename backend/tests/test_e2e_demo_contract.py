from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from types import ModuleType

from tests.conftest import login


ROOT = Path(__file__).resolve().parents[2]
QUALITY_SAMPLE = ROOT / "frontend" / "src" / "assets" / "samples" / "quality_1_crack.jpg"


def _load_demo_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("e2e_demo", ROOT / "scripts" / "e2e_demo.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_quality_demo_asset_is_shipped() -> None:
    """The contract test uses the same shipped asset as the official demo."""

    assert QUALITY_SAMPLE.is_file()


def test_demo_forces_offline_providers_before_app_import() -> None:
    environment_before_import = dict(os.environ)
    demo = _load_demo_module()

    assert demo.DEMO_PROVIDER_ENV == {
        "VISION_PROVIDER": "mock",
        "VISION_LLM_PROVIDER": "off",
        "RETRIEVAL_PROVIDER": "local_keyword",
        "TEXT_PROVIDER": "template",
    }
    assert dict(os.environ) == environment_before_import

    local_environment = {"TEXT_PROVIDER": "external", "KEEP_ME": "yes"}
    demo.configure_demo_environment(local_environment)
    assert local_environment == {
        "VISION_PROVIDER": "mock",
        "VISION_LLM_PROVIDER": "off",
        "RETRIEVAL_PROVIDER": "local_keyword",
        "TEXT_PROVIDER": "template",
        "KEEP_ME": "yes",
    }


def test_quality_and_green_demo_contracts_are_available(client, monkeypatch) -> None:
    """Exercise the two flows the official demo script must call."""

    from app.providers.vision.quality_hybrid import QualityYOLODetector

    monkeypatch.setattr(QualityYOLODetector, "available", False)
    quality_headers = login(client, "quality")
    manager_headers = login(client, "manager")

    quality_status = client.get("/api/v1/quality/status", headers=manager_headers)
    green_status = client.get("/api/v1/green/status", headers=manager_headers)
    assert quality_status.status_code == 200
    assert green_status.status_code == 200
    assert quality_status.json()["data"]["status"] == "available"
    assert green_status.json()["data"]["status"] == "available"

    quality_response = client.post(
        "/api/v1/quality/analyze",
        headers=quality_headers,
        files={"image": (QUALITY_SAMPLE.name, QUALITY_SAMPLE.read_bytes(), "image/jpeg")},
        data={
            "project_id": "PRJ-001",
            "location": "2号楼东侧外墙",
            "work_type": "外墙抹灰",
            "description": "E2E 合约演示",
            "demo_scenario": "crack",
        },
    )
    assert quality_response.status_code == 200
    quality = quality_response.json()["data"]
    assert quality["is_simulated"] is True
    assert quality["defects"]
    assert quality["evidence"]
    demo = _load_demo_module()
    assert tuple(item["agent"] for item in quality["agent_trace"]) == demo.QUALITY_AGENT_TRACE

    green_response = client.post(
        "/api/v1/green/analyze",
        headers=manager_headers,
        json={
            "project_id": "PRJ-001",
            "area_m2": 8500,
            "scope": "E2E 合约演示",
            "materials": [
                {"code": "CONCRETE_C30", "name": "C30商品混凝土", "quantity": 10, "unit": "m3"},
                {"code": "UNKNOWN_DEMO_FACTOR", "name": "待核验材料", "quantity": 2, "unit": "t"},
            ],
            "transport": [],
            "energy": [{"code": "GRID_ELEC", "name": "外购电力", "quantity": 1000, "unit": "kWh"}],
        },
    )
    assert green_response.status_code == 200
    green = green_response.json()["data"]
    assert green["is_simulated"] is True
    assert green["total_emission"] > 0
    assert green["factor_warnings"]
    assert any(item["factor_missing"] for item in green["items"])
