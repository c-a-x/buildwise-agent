from tests.conftest import login


def test_worker_can_read_but_cannot_create_work_order(client):
    headers = login(client, "worker")
    projects = client.get("/api/v1/projects", headers=headers)
    assert projects.status_code == 200
    response = client.post("/api/v1/work-orders", headers=headers, json={"task_id": "TASK-missing", "confirm_ai_draft": True})
    assert response.status_code == 403


# ---------- 角色菜单矩阵：跨模块越权应 403 ----------


def test_worker_cannot_access_safety_or_quality(client):
    headers = login(client, "worker")
    assert client.get("/api/v1/safety/tasks", headers=headers).status_code == 403
    assert client.get("/api/v1/quality/tasks", headers=headers).status_code == 403


def test_quality_cannot_access_safety_analysis(client):
    headers = login(client, "quality")
    response = client.post(
        "/api/v1/safety/analyze",
        headers=headers,
        files={"image": ("wall.jpg", b"demo", "image/jpeg")},
        data={"project_id": "PRJ-001", "location": "B1", "work_type": "主体结构", "demo_scenario": "no_helmet"},
    )
    assert response.status_code == 403


def test_safety_cannot_access_quality_analysis(client):
    headers = login(client, "safety")
    response = client.post(
        "/api/v1/quality/analyze",
        headers=headers,
        files={"image": ("wall.jpg", b"demo", "image/jpeg")},
        data={"project_id": "PRJ-001", "location": "B1", "work_type": "砌筑", "demo_scenario": "crack"},
    )
    assert response.status_code == 403


def test_quality_cannot_access_green(client):
    headers = login(client, "quality")
    assert client.get("/api/v1/green/status", headers=headers).status_code == 403
    assert client.get("/api/v1/green/trend?project_id=PRJ-001", headers=headers).status_code == 403


def test_worker_cannot_access_reports(client):
    assert client.get("/api/v1/reports/daily?project_id=PRJ-001&report_date=2026-08-11", headers=login(client, "worker")).status_code == 403


def test_worker_can_self_care_but_not_write_knowledge(client):
    headers = login(client, "worker")
    care = client.post(
        "/api/v1/care/analyze",
        headers=headers,
        json={"project_id": "PRJ-001", "temperature_c": 36, "humidity_pct": 60, "condition": "晴", "description": "工友自助关怀"},
    )
    assert care.status_code == 200
    assert client.get("/api/v1/knowledge/documents", headers=headers).status_code == 200
    doc = {"title": "测试文档", "source": "项目制度", "category": "个人防护", "content": "测试内容"}
    assert client.post("/api/v1/knowledge/documents", json=doc, headers=headers).status_code == 403


def test_manager_cannot_access_audit(client):
    assert client.get("/api/v1/audit/logs", headers=login(client, "manager")).status_code == 403
