from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path
from collections.abc import MutableMapping
from typing import TypedDict, cast

import httpx


DEMO_PROVIDER_ENV: dict[str, str] = {
    "VISION_PROVIDER": "mock",
    "VISION_LLM_PROVIDER": "off",
    "RETRIEVAL_PROVIDER": "local_keyword",
    "TEXT_PROVIDER": "template",
}
AGENT_TRACE_TAIL: tuple[str, ...] = ("RagAgent", "WorkOrderAgent", "WorkerCareAgent", "ReportAgent")
SAFETY_AGENT_TRACE: tuple[str, ...] = ("SafetyAgent", *AGENT_TRACE_TAIL)
QUALITY_AGENT_TRACE: tuple[str, ...] = ("QualityAgent", *AGENT_TRACE_TAIL)

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
VENV_PYTHON = BACKEND / ("venv/Scripts/python.exe" if os.name == "nt" else "venv/bin/python")

sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient  # noqa: E402


JsonObject = dict[str, object]


class TraceEntry(TypedDict):
    agent: str


class Statistics(TypedDict):
    incident_total: int
    new_work_orders: int
    closed_work_orders: int


class SafetyAnalysis(TypedDict):
    task_id: str
    risk_level: str
    hazards: list[object]
    evidence: object
    agent_trace: list[TraceEntry]
    is_simulated: bool
    review_required: bool


class QualityAnalysis(TypedDict):
    task_id: str
    defects: list[object]
    evidence: object
    agent_trace: list[TraceEntry]
    is_simulated: bool


class GreenItem(TypedDict):
    factor_missing: bool


class GreenAnalysis(TypedDict):
    analysis_id: str
    total_emission: float
    is_simulated: bool
    factor_warnings: list[object]
    items: list[GreenItem]


def configure_demo_environment(environ: MutableMapping[str, str] | None = None) -> None:
    target = os.environ if environ is None else environ
    target.update(DEMO_PROVIDER_ENV)


def _response_data(response: httpx.Response, status_code: int, step: str) -> object:
    if response.status_code != status_code:
        raise RuntimeError(f"{step} failed: expected {status_code}, got {response.status_code}: {response.text}")
    raw_payload = response.json()
    if not isinstance(raw_payload, dict):
        raise RuntimeError(f"{step} returned a non-object envelope: {raw_payload}")
    payload = cast(JsonObject, raw_payload)
    if payload.get("success") is not True:
        raise RuntimeError(f"{step} returned an unsuccessful envelope: {payload}")
    return payload.get("data")


def expect(response: httpx.Response, status_code: int, step: str) -> JsonObject:
    data = _response_data(response, status_code, step)
    if not isinstance(data, dict):
        raise RuntimeError(f"{step} returned a non-object data payload: {data}")
    return cast(JsonObject, data)


def expect_list(response: httpx.Response, status_code: int, step: str) -> list[JsonObject]:
    data = _response_data(response, status_code, step)
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise RuntimeError(f"{step} returned an invalid list payload: {data}")
    return [cast(JsonObject, item) for item in data]


def login(client: TestClient, username: str) -> dict[str, str]:
    data = expect(client.post("/api/v1/auth/login", json={"username": username, "password": "BuildWise123!"}), 200, f"login {username}")
    access_token = data.get("access_token")
    if not isinstance(access_token, str):
        raise RuntimeError(f"login {username} returned no access token")
    return {"Authorization": f"Bearer {access_token}"}


def main() -> None:
    # The live E2E intentionally writes the seeded demo SQLite database. It is
    # repeatable because seed/upsert and work-order confirmation are idempotent.
    configure_demo_environment()
    if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
        os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])

    os.chdir(BACKEND)
    from app.main import app

    image_path = ROOT / "data_demo" / "images" / "safety_no_helmet.jpg"
    quality_image_path = ROOT / "frontend" / "src" / "assets" / "samples" / "quality_1_crack.jpg"
    for demo_image in (image_path, quality_image_path):
        if not demo_image.is_file():
            raise RuntimeError(f"demo image is missing: {demo_image}")

    with TestClient(app) as client:
        safety_headers = login(client, "safety")
        projects = expect_list(client.get("/api/v1/projects", headers=safety_headers), 200, "list projects")
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
        safety_analysis = cast(SafetyAnalysis, analysis)
        task_id = safety_analysis["task_id"]
        if safety_analysis["risk_level"] != "high" or len(safety_analysis["hazards"]) != 1 or not safety_analysis["evidence"]:
            raise RuntimeError(f"unexpected analysis result for task {task_id}: {analysis}")
        trace_names = [item["agent"] for item in safety_analysis["agent_trace"]]
        if tuple(trace_names) != SAFETY_AGENT_TRACE:
            raise RuntimeError(f"unexpected Agent trace for task {task_id}: {trace_names}")
        if safety_analysis["is_simulated"] is not True or safety_analysis["review_required"] is not True:
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
        statistics = cast(Statistics, report["statistics"])
        if statistics["incident_total"] < 1 or statistics["new_work_orders"] < 1 or statistics["closed_work_orders"] < 1:
            raise RuntimeError(f"daily report SQL statistics are incomplete: {statistics}")
        search = expect_list(client.get("/api/v1/knowledge/search", headers=safety_headers, params={"q": "安全帽"}), 200, "search safety helmet standard")
        if not search:
            raise RuntimeError("knowledge search returned no safety helmet standard")
        quality = expect(client.get("/api/v1/quality/status", headers=manager_headers), 200, "quality module status")
        green = expect(client.get("/api/v1/green/status", headers=manager_headers), 200, "green module status")
        if quality["status"] != "available" or green["status"] != "available":
            raise RuntimeError(f"implemented modules are not marked available: quality={quality}, green={green}")

        quality_headers = login(client, "quality")
        with quality_image_path.open("rb") as quality_file:
            quality_analysis = expect(
                client.post(
                    "/api/v1/quality/analyze",
                    headers=quality_headers,
                    files={"image": (quality_image_path.name, quality_file, "image/jpeg")},
                    data={
                        "project_id": "PRJ-001",
                        "location": "2号楼东侧外墙",
                        "work_type": "外墙抹灰",
                        "description": "固定 API E2E 演示",
                        "demo_scenario": "crack",
                    },
                ),
                200,
                "quality analysis",
            )
        quality_result = cast(QualityAnalysis, quality_analysis)
        quality_trace = [item["agent"] for item in quality_result["agent_trace"]]
        if tuple(quality_trace) != QUALITY_AGENT_TRACE:
            raise RuntimeError(f"unexpected quality Agent trace for task {quality_analysis['task_id']}: {quality_trace}")
        if not quality_result["defects"] or not quality_result["evidence"] or quality_result["is_simulated"] is not True:
            raise RuntimeError(f"quality result is incomplete: {quality_analysis}")

        green_analysis = expect(
            client.post(
                "/api/v1/green/analyze",
                headers=manager_headers,
                json={
                    "project_id": "PRJ-001",
                    "area_m2": 8500,
                    "scope": "固定 API E2E 演示",
                    "materials": [
                        {"code": "CONCRETE_C30", "name": "C30商品混凝土", "quantity": 10, "unit": "m3"},
                        {"code": "UNKNOWN_DEMO_FACTOR", "name": "待核验材料", "quantity": 2, "unit": "t"},
                    ],
                    "transport": [],
                    "energy": [{"code": "GRID_ELEC", "name": "外购电力", "quantity": 1000, "unit": "kWh"}],
                },
            ),
            200,
            "green analysis",
        )
        green_result = cast(GreenAnalysis, green_analysis)
        if green_result["total_emission"] <= 0 or green_result["is_simulated"] is not True:
            raise RuntimeError(f"green emission result is incomplete: {green_analysis}")
        if not green_result["factor_warnings"] or not any(item["factor_missing"] for item in green_result["items"]):
            raise RuntimeError(f"green factor warning is missing: {green_analysis}")

        print(
            f"E2E passed: safety_task_id={task_id} quality_task_id={quality_analysis['task_id']} "
            f"green_analysis_id={green_analysis['analysis_id']} order_id={order_id} report_id={report['id']}",
            flush=True,
        )


if __name__ == "__main__":
    main()
