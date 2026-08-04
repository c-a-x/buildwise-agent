from datetime import date, datetime, timezone

from app.models import AgentRun, Incident, Upload

from tests.conftest import login


def test_report_statistics_and_upsert(client):
    headers = login(client)
    response = client.post("/api/v1/safety/analyze", headers=headers, files={"image": ("site.jpg", b"demo", "image/jpeg")}, data={"project_id": "PRJ-001", "location": "B1", "work_type": "主体结构", "demo_scenario": "no_helmet"})
    assert response.status_code == 200
    manager_headers = login(client, "manager")
    payload = {"project_id": "PRJ-001", "report_date": date.today().isoformat()}
    first = client.post("/api/v1/reports/daily/generate", headers=manager_headers, json=payload)
    second = client.post("/api/v1/reports/daily/generate", headers=manager_headers, json=payload)
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["data"]["id"] == second.json()["data"]["id"]
    assert second.json()["data"]["statistics"]["incident_total"] >= 1
    history = client.get("/api/v1/reports", headers=manager_headers, params={"project_id": "PRJ-001"})
    assert history.status_code == 200
    assert history.json()["data"]


def test_knowledge_search_does_not_fabricate(client):
    headers = login(client)
    match = client.get("/api/v1/knowledge/search", headers=headers, params={"q": "安全帽"})
    assert match.status_code == 200
    assert match.json()["data"]
    miss = client.get("/api/v1/knowledge/search", headers=headers, params={"q": "不存在的规范关键词"})
    assert miss.status_code == 200
    assert miss.json()["data"] == []


def test_report_date_uses_local_day_boundary_for_utc_records(client, db_session):
    created_at = datetime(2026, 8, 2, 16, 30, tzinfo=timezone.utc)
    db_session.add(
        Upload(
            id="UPL-TZ-001",
            project_id="PRJ-001",
            uploaded_by="USR-002",
            original_name="timezone.jpg",
            stored_name="timezone.jpg",
            mime_type="image/jpeg",
            size_bytes=4,
            relative_path="uploads/timezone.jpg",
            sha256="0" * 64,
            created_at=created_at,
        )
    )
    db_session.add(
        AgentRun(
            id="TASK-TZ-001",
            project_id="PRJ-001",
            upload_id="UPL-TZ-001",
            requested_by="USR-002",
            location="B1",
            work_type="主体结构",
            status="completed",
            is_simulated=True,
            created_at=created_at,
            finished_at=created_at,
        )
    )
    db_session.add(
        Incident(
            id="INC-TZ-001",
            agent_run_id="TASK-TZ-001",
            project_id="PRJ-001",
            upload_id="UPL-TZ-001",
            hazard_type="no_helmet",
            hazard_name="未佩戴安全帽",
            description="时区边界测试",
            confidence=0.9,
            risk_level="high",
            created_at=created_at,
        )
    )
    db_session.commit()

    response = client.post(
        "/api/v1/reports/daily/generate",
        headers=login(client, "manager"),
        json={"project_id": "PRJ-001", "report_date": "2026-08-03"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["statistics"]["incident_total"] == 1
