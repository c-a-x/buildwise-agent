from __future__ import annotations

from app.models import GreenAssessment
from app.services.green_assessment_service import level_for, score_metric
from tests.conftest import login


# ---------- 评分纯函数 ----------


def test_score_metric_higher_target_equals_100():
    assert score_metric(30, 30) == 100.0


def test_score_metric_higher_zero_value_is_zero():
    assert score_metric(0, 30) == 0.0


def test_score_metric_caps_at_100():
    assert score_metric(90, 30) == 100.0


def test_score_metric_missing_input_is_zero():
    assert score_metric(None, 30) == 0.0


def test_score_metric_lower_is_inverted():
    # 越低越好：value 越小分越高；value=0 → 100。
    assert score_metric(5, 10, "lower") == 100.0
    assert score_metric(0, 10, "lower") == 100.0
    assert score_metric(10, 10, "lower") == 100.0
    assert score_metric(20, 10, "lower") == 50.0


def test_level_boundaries():
    assert level_for(84.9) == "优良"
    assert level_for(85) == "优秀"
    assert level_for(69.9) == "合格"
    assert level_for(59.9) == "不合格"


# ---------- 端点 ----------

FULL_FORM = {
    "project_id": "PRJ-001",
    "title": "主体结构阶段评估",
    "area_m2": 8500,
    "dimensions": [
        {"dimension": "material", "metrics": [{"key": "recycled_material_pct", "value": 30}, {"key": "template_reuse_times", "value": 6}, {"key": "material_recycle_rate", "value": 50}]},
        {"dimension": "water", "metrics": [{"key": "non_traditional_water_pct", "value": 30}, {"key": "water_saving_pct", "value": 15}]},
        {"dimension": "energy", "metrics": [{"key": "energy_saving_pct", "value": 20}, {"key": "renewable_energy_pct", "value": 10}]},
        {"dimension": "land", "metrics": [{"key": "land_saving_pct", "value": 20}, {"key": "greening_rate", "value": 20}]},
        {"dimension": "env", "metrics": [{"key": "env_compliance_pct", "value": 100}, {"key": "sewage_treatment_pct", "value": 100}]},
    ],
}


def test_assessment_full_score_is_excellent(client):
    response = client.post("/api/v1/green/assessments", json=FULL_FORM, headers=login(client, "manager"))
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_score"] == 100.0
    assert data["level"] == "优秀"
    assert data["is_simulated"] is False
    assert len(data["dimensions"]) == 5
    assert data["dimensions"][0]["score"] == 100.0


def test_assessment_persists_and_roundtrip(client):
    headers = login(client, "manager")
    created = client.post("/api/v1/green/assessments", json=FULL_FORM, headers=headers).json()["data"]

    listing = client.get("/api/v1/green/assessments?project_id=PRJ-001", headers=headers).json()["data"]
    assert any(item["assessment_id"] == created["assessment_id"] for item in listing)
    assert listing[0]["level"] == "优秀"

    detail = client.get(f"/api/v1/green/assessments/{created['assessment_id']}", headers=headers).json()["data"]
    assert detail["total_score"] == created["total_score"]
    assert detail["project_name"] == "测试演示项目"
    assert len(detail["dimensions"]) == 5


def test_assessment_missing_metric_is_simulated(client, db_session):
    payload = {
        "project_id": "PRJ-001",
        "dimensions": [
            {"dimension": "material", "metrics": [{"key": "recycled_material_pct", "value": 15}]},
        ],
    }
    response = client.post("/api/v1/green/assessments", json=payload, headers=login(client, "manager"))
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["is_simulated"] is True
    assert "部分指标未填写" in data["report_preview"]
    # material 只有 recycled_material_pct 填了（15/30=50），其余两项缺失按 0 → 均分 ≈ 16.7
    material = next(item for item in data["dimensions"] if item["dimension"] == "material")
    assert material["score"] == round((50.0 + 0.0 + 0.0) / 3, 1)
    assert data["total_score"] == round(material["score"] * 0.2, 1)

    row = db_session.query(GreenAssessment).filter(GreenAssessment.id == data["assessment_id"]).one()
    assert row.requested_by == "USR-001"
    assert row.is_simulated is True


def test_assessment_report_download_docx(client):
    from docx import Document
    from io import BytesIO

    headers = login(client, "manager")
    created = client.post("/api/v1/green/assessments", json=FULL_FORM, headers=headers).json()["data"]

    response = client.get(f"/api/v1/green/assessments/{created['assessment_id']}/report", headers=headers)
    assert response.status_code == 200
    assert "wordprocessingml" in response.headers["content-type"]
    assert response.content[:2] == b"PK"

    document = Document(BytesIO(response.content))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "四节一环保评估报告" in text
    assert "节材" in text


def test_assessment_report_denied_for_other_project(client, db_session):
    from app.core.security import hash_password
    from app.models import User

    headers = login(client, "manager")
    created = client.post("/api/v1/green/assessments", json=FULL_FORM, headers=headers).json()["data"]

    db_session.add(User(id="USR-999", username="outsider", real_name="非项目成员", role="safety_officer", password_hash=hash_password("BuildWise123!"), is_active=True))
    db_session.commit()
    outsider = login(client, "outsider")
    response = client.get(f"/api/v1/green/assessments/{created['assessment_id']}/report", headers=outsider)
    assert response.status_code == 403
