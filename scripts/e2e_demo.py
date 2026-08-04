from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
VENV_PYTHON = BACKEND / ("venv/Scripts/python.exe" if os.name == "nt" else "venv/bin/python")

if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])

sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def expect(response: Any, status_code: int, step: str) -> dict[str, Any]:
    if response.status_code != status_code:
        raise RuntimeError(f"{step} failed: expected {status_code}, got {response.status_code}: {response.text}")
    payload = response.json()
    if payload.get("success") is not True:
        raise RuntimeError(f"{step} returned an unsuccessful envelope: {payload}")
    return payload["data"]


def login(client: TestClient, username: str) -> dict[str, str]:
    data = expect(client.post("/api/v1/auth/login", json={"username": username, "password": "BuildWise123!"}), 200, f"login {username}")
    return {"Authorization": f"Bearer {data['access_token']}"}


def main() -> None:
    image_path = ROOT / "data_demo" / "images" / "safety_no_helmet.jpg"
    if not image_path.exists():
        raise RuntimeError(f"demo image is missing: {image_path}")

    with TestClient(app) as client:
        safety_headers = login(client, "safety")
        projects = expect(client.get("/api/v1/projects", headers=safety_headers), 200, "list projects")
        if not any(project["id"] == "PRJ-001" for project in projects):
            raise RuntimeError("seed project PRJ-001 is missing")

        with image_path.open("rb") as image_file:
            analysis = expect(
                client.post(
                    "/api/v1/safety/analyze",
                    headers=safety_headers,
                    files={"image": (image_path.name, image_file, "image/jpeg")},
                    data={
                        "project_id": "PRJ-001",
                        "location": "B1 北侧临边",
                        "work_type": "主体结构",
                        "description": "固定 API E2E 演示",
                        "demo_scenario": "no_helmet",
                    },
                ),
                200,
                "safety analysis",
            )
        task_id = analysis["task_id"]
        if analysis["risk_level"] != "high" or len(analysis["hazards"]) != 1 or not analysis["evidence"]:
            raise RuntimeError(f"unexpected analysis result for task {task_id}: {analysis}")
        trace_names = [item["agent"] for item in analysis["agent_trace"]]
        if trace_names != ["SafetyAgent", "RagAgent", "WorkOrderAgent", "WorkerCareAgent", "ReportAgent"]:
            raise RuntimeError(f"unexpected Agent trace for task {task_id}: {trace_names}")
        if analysis["is_simulated"] is not True or analysis["review_required"] is not True:
            raise RuntimeError(f"analysis flags are incorrect for task {task_id}")

        order = expect(client.post("/api/v1/work-orders", headers=safety_headers, json={"task_id": task_id, "confirm_ai_draft": True}), 200, "confirm work order")
        repeated_order = expect(client.post("/api/v1/work-orders", headers=safety_headers, json={"task_id": task_id, "confirm_ai_draft": True}), 200, "repeat work order confirmation")
        order_id = order["id"]
        if repeated_order["id"] != order_id:
            raise RuntimeError(f"work order confirmation is not idempotent: {order_id} != {repeated_order['id']}")

        expect(client.patch(f"/api/v1/work-orders/{order_id}/status", headers=safety_headers, json={"status": "in_progress"}), 200, "move order to in_progress")
        expect(client.patch(f"/api/v1/work-orders/{order_id}/status", headers=safety_headers, json={"status": "pending_review"}), 200, "move order to pending_review")
        manager_headers = login(client, "manager")
        closed = expect(client.patch(f"/api/v1/work-orders/{order_id}/status", headers=manager_headers, json={"status": "closed", "note": "E2E 复查通过"}), 200, "close work order")
        if not closed["closed_at"]:
            raise RuntimeError(f"closed_at was not persisted for order {order_id}")

        report = expect(client.post("/api/v1/reports/daily/generate", headers=manager_headers, json={"project_id": "PRJ-001", "report_date": date.today().isoformat()}), 200, "generate daily report")
        search = expect(client.get("/api/v1/knowledge/search", headers=safety_headers, params={"q": "安全帽"}), 200, "search safety helmet standard")
        if not search:
            raise RuntimeError("knowledge search returned no safety helmet standard")
        quality = expect(client.get("/api/v1/quality/status", headers=manager_headers), 200, "quality module status")
        green = expect(client.get("/api/v1/green/status", headers=manager_headers), 200, "green module status")
        if quality["status"] != "planned" or green["status"] != "planned":
            raise RuntimeError(f"placeholder modules are not marked planned: quality={quality}, green={green}")

        print(f"E2E passed: task_id={task_id} order_id={order_id} report_id={report['id']}", flush=True)


if __name__ == "__main__":
    main()
