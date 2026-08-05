from tests.conftest import login


def create_analysis(client, headers):
    response = client.post("/api/v1/safety/analyze", headers=headers, files={"image": ("site.jpg", b"demo", "image/jpeg")}, data={"project_id": "PRJ-001", "location": "B1", "work_type": "主体结构", "demo_scenario": "no_helmet"})
    assert response.status_code == 200
    return response.json()["data"]


def test_confirm_and_status_flow(client):
    headers = login(client)
    analysis = create_analysis(client, headers)
    not_confirmed = client.post("/api/v1/work-orders", headers=headers, json={"task_id": analysis["task_id"], "confirm_ai_draft": False})
    assert not_confirmed.status_code == 400
    order = client.post("/api/v1/work-orders", headers=headers, json={"task_id": analysis["task_id"], "confirm_ai_draft": True})
    assert order.status_code == 200
    order_id = order.json()["data"]["id"]
    assert client.patch(f"/api/v1/work-orders/{order_id}/status", headers=headers, json={"status": "in_progress"}).status_code == 200
    assert client.patch(f"/api/v1/work-orders/{order_id}/status", headers=headers, json={"status": "pending_review"}).status_code == 200
    manager_headers = login(client, "manager")
    closed = client.patch(f"/api/v1/work-orders/{order_id}/status", headers=manager_headers, json={"status": "closed", "note": "复查通过"})
    assert closed.status_code == 200
    assert closed.json()["data"]["status"] == "closed"
    invalid = client.patch(f"/api/v1/work-orders/{order_id}/status", headers=manager_headers, json={"status": "pending"})
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "WORK_ORDER_INVALID_TRANSITION"


def test_worker_cannot_change_order(client):
    safety_headers = login(client)
    analysis = create_analysis(client, safety_headers)
    order = client.post("/api/v1/work-orders", headers=safety_headers, json={"task_id": analysis["task_id"], "confirm_ai_draft": True}).json()["data"]
    worker_headers = login(client, "worker")
    response = client.patch(f"/api/v1/work-orders/{order['id']}/status", headers=worker_headers, json={"status": "in_progress"})
    assert response.status_code == 403


def test_work_order_serialize_includes_assignee_name(client):
    headers = login(client)
    analysis = create_analysis(client, headers)
    order = client.post("/api/v1/work-orders", headers=headers, json={"task_id": analysis["task_id"], "confirm_ai_draft": True}).json()["data"]

    # 未指定责任人时，默认落到项目经理 USR-001
    assert order["assignee_user_id"] == "USR-001"
    assert order["assignee_name"] == "演示项目经理"

    listing = client.get("/api/v1/work-orders", headers=headers).json()["data"]
    listed = next(item for item in listing if item["id"] == order["id"])
    assert listed["assignee_name"] == "演示项目经理"
