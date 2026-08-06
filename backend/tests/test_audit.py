from app.core.security import hash_password
from app.models import AuditLog, User

from tests.conftest import login


def create_analysis(client, headers):
    response = client.post("/api/v1/safety/analyze", headers=headers, files={"image": ("site.jpg", b"demo", "image/jpeg")}, data={"project_id": "PRJ-001", "location": "B1", "work_type": "主体结构", "demo_scenario": "no_helmet"})
    assert response.status_code == 200
    return response.json()["data"]


def _count(db, **filters):
    query = db.query(AuditLog)
    for key, value in filters.items():
        query = query.filter(getattr(AuditLog, key) == value)
    return query.count()


def _add_admin(db_session):
    admin = User(id="USR-ADMIN", username="auditor", real_name="演示管理员", role="admin", password_hash=hash_password("BuildWise123!"), is_active=True)
    db_session.add(admin)
    db_session.commit()
    return admin


def test_login_and_logout_are_audited(client, db_session):
    assert _count(db_session, action="user_login") == 0
    headers = login(client, "safety")
    assert _count(db_session, action="user_login", user_id="USR-002") == 1
    response = client.post("/api/v1/auth/logout", headers=headers)
    assert response.status_code == 200
    assert _count(db_session, action="user_logout", user_id="USR-002") == 1


def test_project_create_is_audited(client, db_session):
    headers = login(client, "manager")
    response = client.post("/api/v1/projects", headers=headers, json={"code": "DEMO-002", "name": "二期项目", "address": "测试地址 2 号", "description": "审计测试项目"})
    assert response.status_code == 200
    project_id = response.json()["data"]["id"]
    row = db_session.query(AuditLog).filter(AuditLog.action == "create_project", AuditLog.resource_id == project_id).one()
    assert row.user_id == "USR-001"
    assert row.resource_type == "project"
    assert row.detail_json["code"] == "DEMO-002"


def test_work_order_status_change_is_audited(client, db_session):
    headers = login(client, "safety")
    analysis = create_analysis(client, headers)
    order = client.post("/api/v1/work-orders", headers=headers, json={"task_id": analysis["task_id"], "confirm_ai_draft": True}).json()["data"]
    assert _count(db_session, action="confirm_work_order", resource_id=order["id"]) == 1
    response = client.patch(f"/api/v1/work-orders/{order['id']}/status", headers=headers, json={"status": "in_progress"})
    assert response.status_code == 200
    assert _count(db_session, action="change_work_order_status", resource_id=order["id"]) == 1


def test_audit_logs_requires_auth(client):
    response = client.get("/api/v1/audit/logs")
    assert response.status_code == 401


def test_audit_logs_admin_only(client):
    for username in ("safety", "manager"):
        response = client.get("/api/v1/audit/logs", headers=login(client, username))
        assert response.status_code == 403


def test_admin_can_list_filter_and_paginate(client, db_session):
    _add_admin(db_session)
    # 通过真实接口造审计数据：manager 登录 + 建项目，safety 登录
    login(client, "manager")
    login(client, "safety")
    login(client, "manager")
    client.post("/api/v1/projects", headers=login(client, "manager"), json={"code": "DEMO-003", "name": "分页项目", "address": "测试地址 3 号", "description": ""})
    headers = login(client, "auditor")

    # 未带过滤器：items + total
    first = client.get("/api/v1/audit/logs", headers=headers)
    assert first.status_code == 200
    payload = first.json()["data"]
    assert payload["total"] >= 4
    assert payload["items"]
    assert payload["items"][0]["username"] is not None
    assert {"id", "user_id", "username", "action", "resource_type", "resource_id", "detail_json", "ip_address", "created_at"} <= set(payload["items"][0])

    # action 过滤
    filtered = client.get("/api/v1/audit/logs", headers=headers, params={"action": "create_project"}).json()["data"]
    assert filtered["total"] == 1
    assert all(item["action"] == "create_project" for item in filtered["items"])

    # resource_type 过滤
    by_resource = client.get("/api/v1/audit/logs", headers=headers, params={"resource_type": "auth"}).json()["data"]
    assert by_resource["total"] >= 3
    assert all(item["resource_type"] == "auth" for item in by_resource["items"])

    # limit/offset 分页
    page = client.get("/api/v1/audit/logs", headers=headers, params={"limit": 2, "offset": 0}).json()["data"]
    assert page["limit"] == 2
    assert len(page["items"]) == 2
    assert page["total"] == first.json()["data"]["total"]
    assert client.get("/api/v1/audit/logs", headers=headers, params={"limit": 2, "offset": 2}).json()["data"]["total"] == page["total"]


def test_audit_actions_admin_only_and_deduped(client, db_session):
    for username in ("safety", "manager"):
        assert client.get("/api/v1/audit/actions", headers=login(client, username)).status_code == 403
    login(client, "manager")
    login(client, "safety")
    _add_admin(db_session)
    response = client.get("/api/v1/audit/actions", headers=login(client, "auditor"))
    assert response.status_code == 200
    actions = response.json()["data"]
    assert isinstance(actions, list)
    assert actions == sorted(set(actions))
    assert "user_login" in actions
