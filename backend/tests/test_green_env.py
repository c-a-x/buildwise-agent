from __future__ import annotations

from app.models import GreenEnvRecord
from app.services.green_env_service import check_alerts, threshold_read, THRESHOLDS
from tests.conftest import login

CLEAN_PAYLOAD = {
    "project_id": "PRJ-001",
    "record_date": "2026-08-11",
    "pm25": 30,
    "pm10": 80,
    "tsp": 120,
    "noise_day_db": 60,
    "noise_night_db": 50,
    "cod_mg": 80,
    "ss_mg": 40,
    "ph": 7.5,
    "solid_waste_t": 3.2,
}


def test_check_alerts_above_and_range():
    alerts = check_alerts({"pm10": 160, "noise_night_db": 70, "ph": 5.5, "cod_mg": 90})
    keys = {alert.key for alert in alerts}
    assert keys == {"pm10", "noise_night_db", "ph"}

    ph_alert = next(alert for alert in alerts if alert.key == "ph")
    assert ph_alert.rule == "range"
    assert ph_alert.min == 6 and ph_alert.max == 9


def test_check_alerts_empty_when_clean():
    assert check_alerts({"pm10": 100, "ph": 7}) == []


def test_threshold_read_shape():
    pm10 = threshold_read("pm10", THRESHOLDS["pm10"])
    assert pm10.rule == "above"
    assert pm10.limit == 150


def test_thresholds_endpoint(client):
    response = client.get("/api/v1/green/env-records/thresholds", headers=login(client, "manager"))
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == len(THRESHOLDS)
    ph = next(item for item in data if item["key"] == "ph")
    assert ph["rule"] == "range" and ph["max"] == 9


def test_env_record_clean_no_alerts(client, db_session):
    headers = login(client, "manager")
    response = client.post("/api/v1/green/env-records", json=CLEAN_PAYLOAD, headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["has_alerts"] is False
    assert data["alerts"] == []
    assert data["record_date"] == "2026-08-11"

    row = db_session.query(GreenEnvRecord).filter(GreenEnvRecord.id == data["record_id"]).one()
    assert row.requested_by == "USR-001"
    assert row.pm10 == 80


def test_env_record_exceeded_creates_alerts(client, db_session):
    payload = {**CLEAN_PAYLOAD, "pm10": 180, "noise_day_db": 85}
    response = client.post("/api/v1/green/env-records", json=payload, headers=login(client, "manager"))
    data = response.json()["data"]
    assert data["has_alerts"] is True
    keys = {alert["key"] for alert in data["alerts"]}
    assert keys == {"pm10", "noise_day_db"}

    row = db_session.query(GreenEnvRecord).filter(GreenEnvRecord.id == data["record_id"]).one()
    assert row.has_alerts is True
    assert {alert["key"] for alert in row.alerts_json} == {"pm10", "noise_day_db"}


def test_env_record_same_date_upsert(client, db_session):
    headers = login(client, "manager")
    first = client.post("/api/v1/green/env-records", json=CLEAN_PAYLOAD, headers=headers).json()["data"]

    updated = {**CLEAN_PAYLOAD, "pm25": 12, "ph": 8.5}
    second = client.post("/api/v1/green/env-records", json=updated, headers=headers).json()["data"]

    # 同一项目+日期：更新原记录而非新建
    assert second["record_id"] == first["record_id"]
    assert second["pm25"] == 12
    rows = db_session.query(GreenEnvRecord).filter(GreenEnvRecord.project_id == "PRJ-001", GreenEnvRecord.record_date == "2026-08-11").all()
    assert len(rows) == 1


def test_env_record_filters(client, db_session):
    headers = login(client, "manager")
    client.post("/api/v1/green/env-records", json=CLEAN_PAYLOAD, headers=headers)
    client.post(
        "/api/v1/green/env-records",
        json={**CLEAN_PAYLOAD, "record_date": "2026-08-12", "pm10": 200, "noise_day_db": 90},
        headers=headers,
    )

    all_rows = client.get("/api/v1/green/env-records?project_id=PRJ-001", headers=headers).json()["data"]
    assert len(all_rows) == 2

    alert_rows = client.get("/api/v1/green/env-records?alert_only=true", headers=headers).json()["data"]
    assert len(alert_rows) == 1
    assert alert_rows[0]["record_date"] == "2026-08-12"

    ranged = client.get("/api/v1/green/env-records?start_date=2026-08-11&end_date=2026-08-11", headers=headers).json()["data"]
    assert len(ranged) == 1


def test_env_record_denied_for_outsider(client, db_session):
    from app.core.security import hash_password
    from app.models import User

    db_session.add(User(id="USR-999", username="outsider", real_name="非项目成员", role="safety_officer", password_hash=hash_password("BuildWise123!"), is_active=True))
    db_session.commit()

    response = client.post("/api/v1/green/env-records", json=CLEAN_PAYLOAD, headers=login(client, "outsider"))
    assert response.status_code == 403
