from tests.conftest import login

# 质量巡检五 agent 闭环测试。conftest 已固定 VISION_PROVIDER=mock / VISION_LLM_PROVIDER=off；
# 质量模块走 QualityHybridVisionProvider，这里额外把 QualityYOLODetector.available 强制置 False，
# 无论 MBDD2025 训练模型是否已生成都确定走 quality_mock 降级，保证断言不随模型文件存在与否漂移。


def _force_quality_mock(monkeypatch):
    from app.providers.vision.quality_hybrid import QualityYOLODetector

    monkeypatch.setattr(QualityYOLODetector, "available", False)


def test_crack_runs_five_agents_and_persists(client, monkeypatch):
    _force_quality_mock(monkeypatch)
    headers = login(client, "quality")
    response = client.post(
        "/api/v1/quality/analyze",
        headers=headers,
        files={"image": ("wall.jpg", b"demo", "image/jpeg")},
        data={"project_id": "PRJ-001", "location": "2号楼东侧外墙", "work_type": "外墙抹灰", "demo_scenario": "crack"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["is_simulated"] is True
    assert data["review_required"] is True
    assert data["risk_level"] == "medium"
    assert data["defects"][0]["hazard_type"] == "crack"
    assert data["defects"][0]["hazard_name"] == "裂缝"
    assert data["defects"][0]["bbox"] is not None
    assert data["evidence"]
    assert [item["agent"] for item in data["agent_trace"]] == ["QualityAgent", "RagAgent", "WorkOrderAgent", "WorkerCareAgent", "ReportAgent"]
    assert data["work_order_draft"]["assignee_role"] == "quality_inspector"
    assert data["work_order_draft"]["confirmed_by_human"] is False
    detail = client.get(f"/api/v1/quality/tasks/{data['task_id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["defects"][0]["hazard_type"] == "crack"


def test_abscission_maps_to_high_risk(client, monkeypatch):
    _force_quality_mock(monkeypatch)
    headers = login(client, "quality")
    response = client.post(
        "/api/v1/quality/analyze",
        headers=headers,
        files={"image": ("wall.jpg", b"demo", "image/jpeg")},
        data={"project_id": "PRJ-001", "location": "1号楼西侧外墙", "work_type": "抹灰工程", "demo_scenario": "abscission"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["risk_level"] == "high"
    assert data["defects"][0]["hazard_type"] == "abscission"


def test_normal_scenario_skips_downstream_agents(client, monkeypatch):
    _force_quality_mock(monkeypatch)
    headers = login(client, "quality")
    response = client.post(
        "/api/v1/quality/analyze",
        headers=headers,
        files={"image": ("normal.jpg", b"demo", "image/jpeg")},
        data={"project_id": "PRJ-001", "location": "楼内巡检", "work_type": "巡检", "demo_scenario": "normal"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["defects"] == []
    assert data["work_order_draft"] is None
    assert [item["status"] for item in data["agent_trace"]] == ["completed", "skipped", "skipped", "skipped", "completed"]


def test_crack_defect_carries_risk_score(client, monkeypatch):
    from app.rules.risk_rules import compute_risk_score

    _force_quality_mock(monkeypatch)
    headers = login(client, "quality")
    response = client.post(
        "/api/v1/quality/analyze",
        headers=headers,
        files={"image": ("wall.jpg", b"demo", "image/jpeg")},
        data={"project_id": "PRJ-001", "location": "2号楼东侧外墙", "work_type": "外墙抹灰", "demo_scenario": "crack"},
    )
    assert response.status_code == 200
    defect = response.json()["data"]["defects"][0]
    # crack 不在 RISK_RULES，按 risk_level=medium 兜底 base 60 × 置信度 0.95 → 59
    assert defect["risk_score"] == compute_risk_score("crack", "medium", 0.95)
    assert 0 <= defect["risk_score"] <= 100


def test_quality_tasks_isolated_from_safety(client, monkeypatch):
    _force_quality_mock(monkeypatch)
    quality_headers = login(client, "quality")
    safety_headers = login(client, "safety")
    response = client.post(
        "/api/v1/quality/analyze",
        headers=quality_headers,
        files={"image": ("wall.jpg", b"demo", "image/jpeg")},
        data={"project_id": "PRJ-001", "location": "B1", "work_type": "砌筑", "demo_scenario": "crack"},
    )
    assert response.status_code == 200
    quality_task_id = response.json()["data"]["task_id"]
    quality_tasks = client.get("/api/v1/quality/tasks?project_id=PRJ-001", headers=quality_headers).json()["data"]
    safety_tasks = client.get("/api/v1/safety/tasks?project_id=PRJ-001", headers=safety_headers).json()["data"]
    assert any(task["task_id"] == quality_task_id for task in quality_tasks)
    assert all(task["task_id"] != quality_task_id for task in safety_tasks)
