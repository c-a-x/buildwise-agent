from datetime import date

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
