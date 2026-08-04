"""实时单帧检测（/detect-frame）与 MJPG 代理（/mjpeg-proxy）端点测试。"""

from __future__ import annotations

from app.core.config import settings
from app.providers.vision.yolo import YOLODetector
from tests.conftest import login


def _token(client: object) -> str:
    response = client.post(
        "/api/v1/auth/login", json={"username": "safety", "password": "BuildWise123!"}
    )
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def _jpeg_bytes() -> bytes:
    return b"\xff\xd8\xff\xe0" + b"\x00" * 64


def test_detect_frame_requires_auth(client):
    response = client.post(
        "/api/v1/safety/detect-frame", files={"image": ("f.jpg", _jpeg_bytes(), "image/jpeg")}
    )
    assert response.status_code == 401


def test_detect_frame_ok_without_model(client, monkeypatch):
    # 模拟模型缺失 → 返回 available=false 而非 500
    monkeypatch.setattr("app.providers.vision.yolo.load_model", lambda path: None)
    headers = login(client)
    response = client.post(
        "/api/v1/safety/detect-frame",
        files={"image": ("f.jpg", _jpeg_bytes(), "image/jpeg")},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["available"] is False
    assert data["is_simulated"] is True
    assert data["provider"] == "safety_hybrid:yolo"
    assert data["risk_level"] == "normal"
    assert data["hazards"] == []
    assert "latency_ms" in data


def test_detect_frame_with_detections(client, monkeypatch):
    # 模拟模型可用且检测到违规 → 聚合 risk_level + 补 id + 清理临时文件
    fake_hazards = [
        {
            "hazard_type": "no_helmet",
            "hazard_name": "未佩戴安全帽",
            "description": "检测到 NO-Hardhat。",
            "confidence": 0.93,
            "risk_level": "high",
            "bbox": [0.1, 0.1, 0.4, 0.6],
            "source": "yolo",
        },
        {
            "hazard_type": "person_present",
            "hazard_name": "现场人员",
            "description": "检测到 person。",
            "confidence": 0.8,
            "risk_level": "low",
            "bbox": [0.2, 0.2, 0.5, 0.8],
            "source": "yolo",
        },
    ]
    monkeypatch.setattr("app.providers.vision.yolo.load_model", lambda path: object())
    monkeypatch.setattr(YOLODetector, "detect", lambda self, image_path: fake_hazards)
    headers = login(client)
    response = client.post(
        "/api/v1/safety/detect-frame",
        files={"image": ("f.jpg", _jpeg_bytes(), "image/jpeg")},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["available"] is True
    assert data["is_simulated"] is False
    assert data["risk_level"] == "high"  # no_helmet(high) 聚合最高
    assert len(data["hazards"]) == 2
    assert data["hazards"][0]["id"].startswith("HZ")
    assert data["hazards"][0]["source"] == "yolo"
    # 临时文件已清理
    tmp_dir = settings.storage_dir / "tmp"
    leftovers = [path for path in tmp_dir.glob("frame-*")] if tmp_dir.exists() else []
    assert leftovers == []


def test_detect_frame_rejects_invalid_and_too_large(client):
    headers = login(client)
    bad = client.post(
        "/api/v1/safety/detect-frame",
        files={"image": ("f.txt", b"hello", "text/plain")},
        headers=headers,
    )
    assert bad.status_code == 400
    big = b"\x00" * (settings.max_upload_mb * 1024 * 1024 + 1)
    too_large = client.post(
        "/api/v1/safety/detect-frame",
        files={"image": ("f.jpg", big, "image/jpeg")},
        headers=headers,
    )
    assert too_large.status_code == 413


def test_mjpeg_proxy_requires_auth(client):
    response = client.get("/api/v1/safety/mjpeg-proxy", params={"url": "http://192.168.1.50:81/stream"})
    assert response.status_code == 401


def test_mjpeg_proxy_denies_public_url(client):
    response = client.get(
        "/api/v1/safety/mjpeg-proxy",
        params={"url": "https://example.com/stream", "token": _token(client)},
    )
    assert response.status_code == 400


def test_mjpeg_proxy_passes_private_url_with_cors(client):
    response = client.get(
        "/api/v1/safety/mjpeg-proxy",
        params={"url": "http://192.168.1.50:81/stream", "token": _token(client)},
    )
    # SSRF 守卫放行内网地址；连不上则返回 200 空流，但必须带 ACAO 头
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "*"
