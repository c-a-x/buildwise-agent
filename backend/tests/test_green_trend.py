from __future__ import annotations

from datetime import datetime, timezone

from app.models import CarbonAnalysis, GreenTarget
from app.services.green_trend_service import GreenTrendService
from tests.conftest import login


def _insert_analysis(db, analysis_id, project_id, emission, area, created_at):
    db.add(
        CarbonAnalysis(
            id=analysis_id,
            project_id=project_id,
            area_m2=area,
            scope="",
            total_emission=emission,
            is_simulated=True,
            factor_version="0.1.0",
            result_json={},
            created_at=created_at,
        )
    )
    db.flush()


def test_trend_points_ordered_and_intensity(client, db_session):
    _insert_analysis(db_session, "TRD-001", "PRJ-001", 1000, 10000, datetime(2026, 7, 1, tzinfo=timezone.utc))
    _insert_analysis(db_session, "TRD-002", "PRJ-001", 2000, 10000, datetime(2026, 8, 1, tzinfo=timezone.utc))
    _insert_analysis(db_session, "TRD-003", "PRJ-001", 3000, None, datetime(2026, 8, 2, tzinfo=timezone.utc))  # 无面积，排除
    db_session.commit()

    response = client.get("/api/v1/green/trend?project_id=PRJ-001", headers=login(client, "manager"))
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["points"]) == 2
    assert [point["intensity"] for point in data["points"]] == [0.1, 0.2]  # 升序
    assert data["current"]["intensity"] == 0.2


def test_trend_grade_without_target(client, db_session):
    _insert_analysis(db_session, "TRD-001", "PRJ-001", 1000, 10000, datetime(2026, 8, 1, tzinfo=timezone.utc))
    db_session.commit()

    data = client.get("/api/v1/green/trend?project_id=PRJ-001", headers=login(client, "manager")).json()["data"]
    assert data["current"]["target_intensity"] is None
    assert data["current"]["grade"] == "未设目标"


def test_trend_grade_math(client):
    assert GreenTrendService._current(0.2, 0.2).grade == "达标"
    assert GreenTrendService._current(0.2, 0.2).gap_pct == 0.0
    assert GreenTrendService._current(0.21, 0.2).grade == "临界"
    assert GreenTrendService._current(0.22, 0.2).grade == "临界"  # 恰为 1.1× 边界仍属临界
    assert GreenTrendService._current(0.23, 0.2).grade == "超标"
    assert GreenTrendService._current(0.23, 0.2).gap_pct == 15.0
    assert GreenTrendService._current(None, None).grade == "未设目标"


def test_target_put_and_get(client, db_session):
    headers = login(client, "manager")
    empty = client.get("/api/v1/green/target?project_id=PRJ-001", headers=headers).json()["data"]
    assert empty["target_intensity"] is None

    response = client.put("/api/v1/green/target", json={"project_id": "PRJ-001", "target_intensity": 0.18, "note": "对标先进水平"}, headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["target_intensity"] == 0.18

    # upsert：再次 PUT 更新而非新建
    second = client.put("/api/v1/green/target", json={"project_id": "PRJ-001", "target_intensity": 0.15, "note": "收紧目标"}, headers=headers).json()["data"]
    assert second["target_intensity"] == 0.15
    rows = db_session.query(GreenTarget).filter(GreenTarget.project_id == "PRJ-001").all()
    assert len(rows) == 1

    fetched = client.get("/api/v1/green/target?project_id=PRJ-001", headers=headers).json()["data"]
    assert fetched["target_intensity"] == 0.15
    assert fetched["note"] == "收紧目标"


def test_trend_with_target_grade(client, db_session):
    _insert_analysis(db_session, "TRD-001", "PRJ-001", 2000, 10000, datetime(2026, 8, 1, tzinfo=timezone.utc))  # 0.2
    db_session.commit()
    headers = login(client, "manager")
    client.put("/api/v1/green/target", json={"project_id": "PRJ-001", "target_intensity": 0.18}, headers=headers)

    data = client.get("/api/v1/green/trend?project_id=PRJ-001", headers=headers).json()["data"]
    assert data["current"]["target_intensity"] == 0.18
    assert data["current"]["intensity"] == 0.2
    assert data["current"]["grade"] == "超标"
    assert data["current"]["gap_pct"] == round((0.2 - 0.18) / 0.18 * 100, 1)


def test_trend_denied_for_outsider(client, db_session):
    from app.core.security import hash_password
    from app.models import User

    db_session.add(User(id="USR-999", username="outsider", real_name="非项目成员", role="safety_officer", password_hash=hash_password("BuildWise123!"), is_active=True))
    db_session.commit()

    response = client.get("/api/v1/green/trend?project_id=PRJ-001", headers=login(client, "outsider"))
    assert response.status_code == 403
