from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import app


response = TestClient(app).get("/api/v1/health")
assert response.status_code == 200, response.text
payload = response.json()
assert payload["success"] is True, payload
assert payload["data"]["status"] == "ok", payload
print("Health check passed: /api/v1/health")
