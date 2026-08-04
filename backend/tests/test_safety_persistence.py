from tests.conftest import login


def test_task_detail_restores_full_analysis_result(client, db_session):
    headers = login(client)
    response = client.post(
        "/api/v1/safety/analyze",
        headers=headers,
        files={"image": ("site.jpg", b"demo", "image/jpeg")},
        data={
            "project_id": "PRJ-001",
            "location": "B1 北侧临边",
            "work_type": "主体结构",
            "demo_scenario": "no_helmet",
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]

    detail = client.get(f"/api/v1/safety/tasks/{result['task_id']}", headers=headers)

    assert detail.status_code == 200
    restored = detail.json()["data"]
    assert restored["work_order_draft"] is not None
    assert restored["worker_message"]
    assert restored["report_preview"]

    from app.models import AgentRun, Incident, IncidentEvidence, Upload

    assert db_session.query(Upload).filter_by(id=result["upload_id"]).count() == 1
    assert db_session.query(AgentRun).filter_by(id=result["task_id"]).count() == 1
    assert db_session.query(Incident).filter_by(agent_run_id=result["task_id"]).count() == 1
    assert db_session.query(IncidentEvidence).count() >= 1

