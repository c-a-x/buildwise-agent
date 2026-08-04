from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import cast

import httpx


ROOT = Path(__file__).resolve().parents[1]
API_URL = os.getenv("BUILDWISE_DOCKER_API_URL", "http://localhost:8000/api/v1").rstrip("/")
FRONTEND_URL = os.getenv("BUILDWISE_DOCKER_FRONTEND_URL", "http://localhost:8080").rstrip("/")
PASSWORD = "BuildWise123!"
JsonObject = dict[str, object]


def expect_data(response: httpx.Response, expected_status: int, step: str) -> object:
    if response.status_code != expected_status:
        raise RuntimeError(f"{step} failed: expected {expected_status}, got {response.status_code}: {response.text}")
    payload = response.json()
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise RuntimeError(f"{step} returned an unsuccessful envelope: {payload}")
    return payload.get("data")


def expect_object(response: httpx.Response, expected_status: int, step: str) -> JsonObject:
    data = expect_data(response, expected_status, step)
    if not isinstance(data, dict):
        raise RuntimeError(f"{step} returned non-object data: {data}")
    return cast(JsonObject, data)


def expect_list(response: httpx.Response, expected_status: int, step: str) -> list[object]:
    data = expect_data(response, expected_status, step)
    if not isinstance(data, list):
        raise RuntimeError(f"{step} returned non-list data: {data}")
    return data


def value_as_string(data: JsonObject, key: str, step: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"{step} is missing string field {key}: {data}")
    return value


def login(client: httpx.Client, username: str) -> dict[str, str]:
    data = expect_object(
        client.post(f"{API_URL}/auth/login", json={"username": username, "password": PASSWORD}),
        200,
        f"login {username}",
    )
    return {"Authorization": f"Bearer {value_as_string(data, 'access_token', f'login {username}') }"}


def analyze(client: httpx.Client, headers: dict[str, str], image_path: Path, scenario: str) -> JsonObject:
    with image_path.open("rb") as image_file:
        return expect_object(
            client.post(
                f"{API_URL}/safety/analyze",
                headers=headers,
                files={"image": (image_path.name, image_file, "image/jpeg")},
                data={
                    "project_id": "PRJ-001",
                    "location": "B1 北侧临边",
                    "work_type": "主体结构",
                    "description": "Docker HTTP E2E 演示",
                    "demo_scenario": scenario,
                },
            ),
            200,
            f"safety analysis {scenario}",
        )


def main() -> None:
    no_helmet = ROOT / "data_demo/images/safety_no_helmet.jpg"
    normal_image = ROOT / "data_demo/images/safety_normal.jpg"
    if not no_helmet.exists() or not normal_image.exists():
        raise RuntimeError("demo images are missing")

    with httpx.Client(timeout=60.0) as client:
        health = expect_object(client.get(f"{API_URL}/health"), 200, "health")
        database = health.get("database")
        if not isinstance(database, dict) or database.get("status") != "connected" or database.get("persistent") is not True:
            raise RuntimeError(f"database health is not persistent: {health}")
        modules = expect_list(client.get(f"{API_URL}/modules"), 200, "modules")
        if len(modules) != 3:
            raise RuntimeError(f"unexpected module count: {len(modules)}")

        safety_headers = login(client, "safety")
        manager_headers = login(client, "manager")
        current_user = expect_object(client.get(f"{API_URL}/auth/me", headers=safety_headers), 200, "current user")
        if value_as_string(current_user, "username", "current user") != "safety":
            raise RuntimeError(f"current user is incorrect: {current_user}")
        projects = expect_list(client.get(f"{API_URL}/projects", headers=safety_headers), 200, "list projects")
        project_ids = [item.get("id") for item in projects if isinstance(item, dict)]
        if "PRJ-001" not in project_ids:
            raise RuntimeError(f"seed project PRJ-001 is missing: {projects}")

        analysis = analyze(client, safety_headers, no_helmet, "no_helmet")
        task_id = value_as_string(analysis, "task_id", "no-helmet analysis")
        if analysis.get("risk_level") != "high" or not isinstance(analysis.get("hazards"), list) or len(analysis["hazards"]) != 1:
            raise RuntimeError(f"unexpected no-helmet result: {analysis}")
        trace = analysis.get("agent_trace")
        if not isinstance(trace, list) or [item.get("agent") for item in trace if isinstance(item, dict)] != [
            "SafetyAgent",
            "RagAgent",
            "WorkOrderAgent",
            "WorkerCareAgent",
            "ReportAgent",
        ]:
            raise RuntimeError(f"five-Agent trace is incorrect: {trace}")
        if analysis.get("is_simulated") is not True or analysis.get("review_required") is not True:
            raise RuntimeError(f"simulation/review flags are incorrect: {analysis}")

        file_url = value_as_string(analysis, "file_url", "no-helmet analysis")
        file_response = client.get(f"{FRONTEND_URL}{file_url}")
        if file_response.status_code != 200:
            raise RuntimeError(f"uploaded image proxy failed: {file_response.status_code} {file_url}")

        order = expect_object(
            client.post(
                f"{API_URL}/work-orders",
                headers=safety_headers,
                json={"task_id": task_id, "confirm_ai_draft": True},
            ),
            200,
            "confirm work order",
        )
        repeated = expect_object(
            client.post(
                f"{API_URL}/work-orders",
                headers=safety_headers,
                json={"task_id": task_id, "confirm_ai_draft": True},
            ),
            200,
            "repeat work order confirmation",
        )
        order_id = value_as_string(order, "id", "confirm work order")
        if repeated.get("id") != order_id:
            raise RuntimeError(f"work order confirmation is not idempotent: {order_id} vs {repeated.get('id')}")

        for status in ("in_progress", "pending_review"):
            expect_object(
                client.patch(
                    f"{API_URL}/work-orders/{order_id}/status",
                    headers=safety_headers,
                    json={"status": status},
                ),
                200,
                f"move work order to {status}",
            )
        closed = expect_object(
            client.patch(
                f"{API_URL}/work-orders/{order_id}/status",
                headers=manager_headers,
                json={"status": "closed", "note": "Docker E2E 复查通过"},
            ),
            200,
            "close work order",
        )
        if not closed.get("closed_at"):
            raise RuntimeError(f"closed_at was not persisted: {closed}")

        report = expect_object(
            client.post(
                f"{API_URL}/reports/daily/generate",
                headers=manager_headers,
                json={"project_id": "PRJ-001", "report_date": date.today().isoformat()},
            ),
            200,
            "generate daily report",
        )
        report_id = value_as_string(report, "id", "generate daily report")

        normal = analyze(client, safety_headers, normal_image, "normal")
        normal_trace = normal.get("agent_trace")
        normal_statuses = [item.get("status") for item in normal_trace if isinstance(item, dict)] if isinstance(normal_trace, list) else []
        if normal.get("hazards") != [] or normal.get("work_order_draft") is not None or normal_statuses != [
            "completed",
            "skipped",
            "skipped",
            "skipped",
            "completed",
        ]:
            raise RuntimeError(f"normal scenario is incorrect: {normal}")

        knowledge = expect_list(
            client.get(f"{API_URL}/knowledge/search", headers=safety_headers, params={"q": "安全帽"}),
            200,
            "knowledge search",
        )
        if not knowledge:
            raise RuntimeError("knowledge search returned no result")

    print(f"Docker E2E passed: task_id={task_id} order_id={order_id} report_id={report_id}")


if __name__ == "__main__":
    main()
