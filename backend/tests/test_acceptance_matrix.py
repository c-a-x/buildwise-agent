from __future__ import annotations

from datetime import date

from app.models import AgentRun, Incident, IncidentEvidence, Upload, WorkOrder

from tests.conftest import login


def _analyze(client, headers: dict[str, str], scenario: str = "no_helmet") -> dict[str, object]:
    response = client.post(
        "/api/v1/safety/analyze",
        headers=headers,
        files={"image": (f"{scenario}.jpg", b"demo-image", "image/jpeg")},
        data={
            "project_id": "PRJ-001",
            "location": "B1 北侧临边",
            "work_type": "主体结构",
            "demo_scenario": scenario,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_authentication_and_role_boundaries(client):
    assert client.get("/api/v1/projects").status_code == 401

    register = client.post(
        "/api/v1/auth/register",
        json={
            "username": "matrix_worker",
            "real_name": "矩阵测试工友",
            "password": "Password123!",
            "password_confirm": "Password123!",
            "role": "worker",
        },
    )
    assert register.status_code == 200
    duplicate = client.post(
        "/api/v1/auth/register",
        json={
            "username": "matrix_worker",
            "real_name": "矩阵测试工友",
            "password": "Password123!",
            "password_confirm": "Password123!",
            "role": "worker",
        },
    )
    assert duplicate.status_code == 409
    admin_register = client.post(
        "/api/v1/auth/register",
        json={
            "username": "matrix_admin",
            "real_name": "矩阵管理员",
            "password": "Password123!",
            "password_confirm": "Password123!",
            "role": "admin",
        },
    )
    assert admin_register.status_code == 422
    assert client.post("/api/v1/auth/login", json={"username": "safety", "password": "wrong"}).status_code == 401

    login_response = client.post("/api/v1/auth/login", json={"username": "safety", "password": "BuildWise123!"})
    assert login_response.status_code == 200
    token = login_response.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    refreshed = client.post("/api/v1/auth/refresh", headers=headers)
    assert refreshed.status_code == 200
    assert refreshed.json()["data"]["access_token"] != token
    logout = client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 200
    assert logout.json()["data"]["logged_out"] is True


def test_analysis_database_matrix_and_normal_scenario(client, db_session):
    headers = login(client)
    data = _analyze(client, headers)
    assert data["risk_level"] == "high"
    assert data["is_simulated"] is True
    assert data["review_required"] is True
    assert [item["agent"] for item in data["agent_trace"]] == ["SafetyAgent", "RagAgent", "WorkOrderAgent", "WorkerCareAgent", "ReportAgent"]
    assert db_session.query(Upload).count() == 1
    assert db_session.query(AgentRun).count() == 1
    assert db_session.query(Incident).count() == 1
    assert db_session.query(IncidentEvidence).count() >= 1

    normal = _analyze(client, headers, "normal")
    assert normal["hazards"] == []
    assert normal["work_order_draft"] is None
    assert [item["status"] for item in normal["agent_trace"]] == ["completed", "skipped", "skipped", "skipped", "completed"]
    assert db_session.query(Incident).count() == 1
    assert db_session.query(WorkOrder).count() == 0


def test_work_order_boundaries_and_report_empty_day(client, db_session):
    safety_headers = login(client)
    data = _analyze(client, safety_headers)
    first = client.post("/api/v1/work-orders", headers=safety_headers, json={"task_id": data["task_id"], "confirm_ai_draft": True})
    assert first.status_code == 200
    order_id = first.json()["data"]["id"]
    repeated = client.post("/api/v1/work-orders", headers=safety_headers, json={"task_id": data["task_id"], "confirm_ai_draft": True})
    assert repeated.status_code == 200
    assert repeated.json()["data"]["id"] == order_id

    worker_headers = login(client, "worker")
    assert client.patch(f"/api/v1/work-orders/{order_id}/status", headers=worker_headers, json={"status": "in_progress"}).status_code == 403
    assert client.post("/api/v1/work-orders", headers=worker_headers, json={"task_id": data["task_id"], "confirm_ai_draft": True}).status_code == 403
    assert client.patch(f"/api/v1/work-orders/{order_id}/status", headers=safety_headers, json={"status": "closed", "note": "越级关闭"}).status_code == 400
    client.patch(f"/api/v1/work-orders/{order_id}/status", headers=safety_headers, json={"status": "in_progress"})
    client.patch(f"/api/v1/work-orders/{order_id}/status", headers=safety_headers, json={"status": "pending_review"})
    closed = client.patch(f"/api/v1/work-orders/{order_id}/status", headers=login(client, "manager"), json={"status": "closed", "note": "复查通过"})
    assert closed.status_code == 200
    assert closed.json()["data"]["closed_at"] is not None

    empty_date = "2099-01-01"
    report = client.post(
        "/api/v1/reports/daily/generate",
        headers=login(client, "manager"),
        json={"project_id": "PRJ-001", "report_date": empty_date},
    )
    assert report.status_code == 200
    statistics = report.json()["data"]["statistics"]
    assert statistics["incident_total"] == 0
    assert statistics["risk_counts"] == {}
    assert statistics["new_work_orders"] == 0
    assert statistics["closed_work_orders"] == 0
    assert statistics["top_hazards"] == []

    second = client.post(
        "/api/v1/reports/daily/generate",
        headers=login(client, "manager"),
        json={"project_id": "PRJ-001", "report_date": date(2099, 1, 1).isoformat(), "statistics": {"incident_total": 999999}},
    )
    assert second.status_code == 200
    assert second.json()["data"]["statistics"]["incident_total"] == 0
