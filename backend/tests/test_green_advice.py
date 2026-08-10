from __future__ import annotations

import app.services.green_advice_service as green_advice_module
from tests.conftest import login

ANALYZE_PAYLOAD = {
    "project_id": "PRJ-001",
    "area_m2": 8500,
    "scope": "一期主体结构施工阶段",
    "materials": [
        {"code": "CONCRETE_C30", "name": "C30商品混凝土", "quantity": 860, "unit": "m3"},
        {"code": "REBAR_HOT_ROLLED", "name": "热轧钢筋", "quantity": 120, "unit": "t"},
    ],
    "transport": [],
    "energy": [],
}

FULL_FORM = {
    "project_id": "PRJ-001",
    "dimensions": [
        {"dimension": "material", "metrics": [{"key": "recycled_material_pct", "value": 10}, {"key": "template_reuse_times", "value": 3}]},
        {"dimension": "water", "metrics": []},
        {"dimension": "energy", "metrics": []},
        {"dimension": "land", "metrics": []},
        {"dimension": "env", "metrics": []},
    ],
}


def _create_analysis(client, headers) -> str:
    return client.post("/api/v1/green/analyze", json=ANALYZE_PAYLOAD, headers=headers).json()["data"]["analysis_id"]


def _create_assessment(client, headers) -> str:
    return client.post("/api/v1/green/assessments", json=FULL_FORM, headers=headers).json()["data"]["assessment_id"]


def test_advice_carbon_fallback_when_llm_off(client):
    headers = login(client, "manager")
    analysis_id = _create_analysis(client, headers)

    response = client.post("/api/v1/green/advice", json={"project_id": "PRJ-001", "source_type": "carbon", "analysis_id": analysis_id}, headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["is_simulated"] is True  # 离线静态兜底
    assert data["source_type"] == "carbon"
    assert "建材生产" in data["advice"]  # A1-A3 占比最高


def test_advice_assessment_fallback_when_llm_off(client):
    headers = login(client, "manager")
    assessment_id = _create_assessment(client, headers)

    response = client.post("/api/v1/green/advice", json={"project_id": "PRJ-001", "source_type": "assessment", "assessment_id": assessment_id}, headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["is_simulated"] is True
    assert "节材" in data["advice"]  # material 维度得分最低


class FakeAdviceProvider:
    name = "fake_text"
    last_payload: dict[str, object] | None = None

    def generate_green_advice(self, payload: dict[str, object]) -> str:
        self.last_payload = payload
        return "1. 优先采用绿色建材并优化结构设计。\n2. 加强运输线路调度，减少二次转运。"


def test_advice_carbon_uses_llm_when_ready(client, monkeypatch):
    headers = login(client, "manager")
    analysis_id = _create_analysis(client, headers)

    fake = FakeAdviceProvider()
    monkeypatch.setattr(green_advice_module.GreenAdviceService, "_llm_ready", lambda self: True)
    monkeypatch.setattr(green_advice_module, "build_text_provider", lambda settings: fake)

    response = client.post("/api/v1/green/advice", json={"project_id": "PRJ-001", "source_type": "carbon", "analysis_id": analysis_id}, headers=headers)
    data = response.json()["data"]
    assert data["advice"].startswith("1. 优先采用绿色建材")
    assert data["is_simulated"] is True  # 演示因子数据 → 标注模拟
    assert fake.last_payload["source_type"] == "carbon"
    assert fake.last_payload["project_name"] == "测试演示项目"
    assert fake.last_payload["stage_shares"]["A1-A3"] > 0


def test_advice_assessment_uses_llm_with_low_dimensions(client, monkeypatch):
    headers = login(client, "manager")
    assessment_id = _create_assessment(client, headers)

    fake = FakeAdviceProvider()
    monkeypatch.setattr(green_advice_module.GreenAdviceService, "_llm_ready", lambda self: True)
    monkeypatch.setattr(green_advice_module, "build_text_provider", lambda settings: fake)

    response = client.post("/api/v1/green/advice", json={"project_id": "PRJ-001", "source_type": "assessment", "assessment_id": assessment_id}, headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["is_simulated"] is True  # 缺省维度按 0 计 → 模拟
    assert fake.last_payload["source_type"] == "assessment"
    low_dimensions = fake.last_payload["low_dimensions"]
    assert low_dimensions  # 低分维度非空


def test_advice_llm_failure_degrades_to_fallback(client, monkeypatch):
    headers = login(client, "manager")
    analysis_id = _create_analysis(client, headers)

    class _BoomAdviceProvider:
        name = "boom"

        def generate_green_advice(self, payload: dict[str, object]) -> str:
            raise RuntimeError("LLM 网络故障")

    monkeypatch.setattr(green_advice_module.GreenAdviceService, "_llm_ready", lambda self: True)
    monkeypatch.setattr(green_advice_module, "build_text_provider", lambda settings: _BoomAdviceProvider())

    response = client.post("/api/v1/green/advice", json={"project_id": "PRJ-001", "source_type": "carbon", "analysis_id": analysis_id}, headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["is_simulated"] is True
    assert "建材生产" in data["advice"]


def test_advice_denied_for_outsider(client, db_session):
    from app.core.security import hash_password
    from app.models import User

    db_session.add(User(id="USR-999", username="outsider", real_name="非项目成员", role="safety_officer", password_hash=hash_password("BuildWise123!"), is_active=True))
    db_session.commit()

    response = client.post("/api/v1/green/advice", json={"project_id": "PRJ-001", "source_type": "carbon"}, headers=login(client, "outsider"))
    assert response.status_code == 403
