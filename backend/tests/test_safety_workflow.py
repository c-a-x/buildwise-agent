from tests.conftest import login


def test_no_helmet_runs_five_agents_and_persists(client):
    headers = login(client)
    response = client.post("/api/v1/safety/analyze", headers=headers, files={"image": ("site.jpg", b"demo", "image/jpeg")}, data={"project_id": "PRJ-001", "location": "B1 北侧临边", "work_type": "主体结构", "demo_scenario": "no_helmet"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["is_simulated"] is True
    assert data["review_required"] is True
    assert data["risk_level"] == "high"
    assert data["hazards"][0]["hazard_type"] == "no_helmet"
    assert data["evidence"]
    assert [item["agent"] for item in data["agent_trace"]] == ["SafetyAgent", "RagAgent", "WorkOrderAgent", "WorkerCareAgent", "ReportAgent"]
    assert data["work_order_draft"]["confirmed_by_human"] is False
    task = client.get(f"/api/v1/safety/tasks/{data['task_id']}", headers=headers)
    assert task.status_code == 200


def test_normal_scenario_skips_downstream_agents(client):
    headers = login(client)
    response = client.post("/api/v1/safety/analyze", headers=headers, files={"image": ("normal.jpg", b"demo", "image/jpeg")}, data={"project_id": "PRJ-001", "location": "B1 东侧", "work_type": "巡检", "demo_scenario": "normal"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["hazards"] == []
    assert data["work_order_draft"] is None
    assert [item["status"] for item in data["agent_trace"]] == ["completed", "skipped", "skipped", "skipped", "completed"]


def test_upload_validation(client):
    headers = login(client)
    response = client.post("/api/v1/safety/analyze", headers=headers, files={"image": ("site.txt", b"demo", "text/plain")}, data={"project_id": "PRJ-001", "location": "位置", "work_type": "作业"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UPLOAD_INVALID_TYPE"


def test_no_helmet_hazard_carries_risk_score(client):
    from app.rules.risk_rules import compute_risk_score

    headers = login(client)
    response = client.post("/api/v1/safety/analyze", headers=headers, files={"image": ("site.jpg", b"demo", "image/jpeg")}, data={"project_id": "PRJ-001", "location": "B1 北侧临边", "work_type": "主体结构", "demo_scenario": "no_helmet"})
    assert response.status_code == 200
    hazard = response.json()["data"]["hazards"][0]
    # mock 视觉不经过 mapping.py，由 _hazard_dict 读回兜底现算（base_score=90 × 置信度 0.96 → 89）
    assert hazard["risk_score"] == compute_risk_score("no_helmet", "high", 0.96)
    assert 0 <= hazard["risk_score"] <= 100


def test_legacy_incident_without_risk_score_gets_computed():
    from app.models import Incident
    from app.rules.risk_rules import compute_risk_score
    from app.services.safety_service import SafetyService

    incident = Incident(
        id="INC-LEGACY", agent_run_id="TASK-X", project_id="PRJ-001", upload_id="UPL-X",
        hazard_type="no_helmet", hazard_name="未佩戴安全帽", description="旧数据无风险分", confidence=0.9, risk_level="high",
        metadata_json={},
    )
    hazard = SafetyService._hazard_dict(incident)
    assert hazard["risk_score"] is not None
    assert 0 <= hazard["risk_score"] <= 100
    assert hazard["risk_score"] == compute_risk_score("no_helmet", "high", 0.9)
