from tests.conftest import login


def test_health_and_modules(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"
    modules = client.get("/api/v1/modules")
    assert modules.status_code == 200
    assert {item["key"] for item in modules.json()["data"]} == {"safety", "quality", "green"}


def test_protected_endpoint_requires_token(client):
    response = client.get("/api/v1/projects")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_TOKEN_EXPIRED"


def test_role_permission_is_enforced(client):
    headers = login(client, "worker")
    response = client.post("/api/v1/projects", headers=headers, json={"code": "NEW-1", "name": "新项目", "address": "地址"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTH_FORBIDDEN"
