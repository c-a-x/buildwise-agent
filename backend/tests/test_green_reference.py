from __future__ import annotations

import json

from app.core.config import settings
from app.providers.carbon import load_reference_library


def test_load_reference_library_from_temp(tmp_path):
    reference_file = tmp_path / "reference.json"
    reference_file.write_text(
        json.dumps(
            {
                "version": "test-1",
                "updated_at": "2026-01-01",
                "source_note": "测试来源",
                "groups": [
                    {
                        "category": "scale",
                        "name": "经营规模",
                        "items": [{"code": "REVENUE", "name": "营业收入", "value": "100", "unit": "亿元", "year": 2025, "source": "测试年报"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    library = load_reference_library(reference_file)
    assert library.version == "test-1"
    assert library.load_error == ""
    assert len(library.groups) == 1
    revenue = library.get("REVENUE")
    assert revenue is not None
    assert revenue.value == "100"
    assert revenue.source == "测试年报"
    assert revenue.year == 2025


def test_load_reference_library_missing_file_is_empty():
    from pathlib import Path

    library = load_reference_library(Path("not-exists.json"))
    assert library.load_error != ""
    assert library.groups == ()


def test_shipped_reference_library_has_known_metrics():
    library = load_reference_library(settings.green_reference_path)
    assert library.load_error == ""
    assert library.version == "2024"
    assert len(library.groups) == 5

    intensity = library.get("CO2_INTENSITY_YOY_2023")
    assert intensity is not None
    assert intensity.value == "↓4.3%"
    assert intensity.year == 2023
    assert "ESG" in intensity.source

    new_contract = library.get("NEW_CONTRACT")
    assert new_contract is not None
    assert new_contract.value == "45,027"
    assert new_contract.unit == "亿元"
    assert "年度报告" in new_contract.source


def test_reference_endpoint_requires_auth(client):
    response = client.get("/api/v1/green/reference")
    assert response.status_code == 401


def test_reference_endpoint_returns_groups(client):
    from tests.conftest import login

    response = client.get("/api/v1/green/reference", headers=login(client, "manager"))
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["version"] == "2024"
    assert "source_note" in data
    assert data["source_note"]
    groups = data["groups"]
    assert len(groups) >= 5
    by_category = {group["category"]: group for group in groups}
    assert "carbon" in by_category
    assert "scale" in by_category
    # 组内条目带 value/source/year，供前端标注来源
    carbon = by_category["carbon"]
    assert all(item["code"] and "value" in item and "source" in item for item in carbon["items"])
    assert any(item["code"] == "CO2_INTENSITY_YOY_2023" for item in carbon["items"])
    scale = by_category["scale"]
    assert any(item["code"] == "NEW_CONTRACT" and item["year"] == 2024 for item in scale["items"])
