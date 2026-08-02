from tests.conftest import login


def test_worker_can_read_but_cannot_create_work_order(client):
    headers = login(client, "worker")
    projects = client.get("/api/v1/projects", headers=headers)
    assert projects.status_code == 200
    response = client.post("/api/v1/work-orders", headers=headers, json={"task_id": "TASK-missing", "confirm_ai_draft": True})
    assert response.status_code == 403
