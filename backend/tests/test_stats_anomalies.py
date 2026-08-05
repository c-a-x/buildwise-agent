from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import AgentRun, Incident, Upload

from tests.conftest import login


def _day(offset: int) -> datetime:
    """距今天 offset 天的 UTC 正午（避开本地时区日界，保证落在同一天）。"""
    today = datetime.now(timezone.utc).date()
    return datetime.combine(today - timedelta(days=offset), datetime.min.time()).replace(tzinfo=timezone.utc) + timedelta(hours=12)


def _day_key(offset: int) -> str:
    return _day(offset).date().isoformat()


def _seed_incidents(db, *, created_at, module=None, count=1, project_id="PRJ-001", prefix="INC", risk_level="high"):
    """直接落 Incident 行（沿用 test_reports.py 的 Upload+AgentRun+Incident 模式）。"""
    for i in range(count):
        uid = f"{prefix}-{i}"
        db.add(
            Upload(
                id=f"UPL-{uid}", project_id=project_id, uploaded_by="USR-002",
                original_name=f"{uid}.jpg", stored_name=f"{uid}.jpg", mime_type="image/jpeg",
                size_bytes=4, relative_path=f"uploads/{uid}.jpg", sha256="0" * 64,
                created_at=created_at,
            )
        )
        db.add(
            AgentRun(
                id=f"TASK-{uid}", project_id=project_id, upload_id=f"UPL-{uid}",
                requested_by="USR-002", location="B1", work_type="主体结构",
                status="completed", is_simulated=True, created_at=created_at, finished_at=created_at,
            )
        )
        db.add(
            Incident(
                id=uid, agent_run_id=f"TASK-{uid}", project_id=project_id, upload_id=f"UPL-{uid}",
                hazard_type="no_helmet", hazard_name="未佩戴安全帽", description="异常检测测试",
                confidence=0.9, risk_level=risk_level,
                metadata_json={"module": module} if module else {},
                created_at=created_at,
            )
        )
    db.commit()


def _anomalies(client, *, module="safety", days=30, z_threshold=2.5, user="safety"):
    return client.get(
        "/api/v1/stats/anomalies",
        params={"project_id": "PRJ-001", "module": module, "days": days, "z_threshold": z_threshold},
        headers=login(client, user),
    )


def test_anomalies_empty_degraded(client):
    response = _anomalies(client)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["available"] is False
    assert "没有记录" in data["reason"]
    assert data["anomaly_days"] == 0
    assert data["total_days"] == 30


def test_anomalies_flags_spike_day(client, db_session):
    _seed_incidents(db_session, created_at=_day(0), count=10)
    data = _anomalies(client, days=30).json()["data"]

    assert data["available"] is True
    assert data["anomaly_days"] == 1
    today_sample = next(sample for sample in data["samples"] if sample["date"] == _day_key(0))
    assert today_sample["count"] == 10
    assert today_sample["z"] > 2.5
    assert today_sample["anomaly"] is True


def test_anomalies_filters_by_module(client, db_session):
    _seed_incidents(db_session, created_at=_day(0), count=2, prefix="INC-SAF")          # 无 module 键 → safety
    _seed_incidents(db_session, created_at=_day(0), count=3, module="quality", prefix="INC-QA")

    quality = _anomalies(client, module="quality").json()["data"]
    assert next(sample for sample in quality["samples"] if sample["date"] == _day_key(0))["count"] == 3

    safety = _anomalies(client, module="safety").json()["data"]
    assert next(sample for sample in safety["samples"] if sample["date"] == _day_key(0))["count"] == 2


def test_anomalies_std_zero_no_flag(client, db_session):
    for offset in (0, 1, 2):
        _seed_incidents(db_session, created_at=_day(offset), count=1, prefix=f"INC-D{offset}")
    data = _anomalies(client, days=3).json()["data"]

    assert data["available"] is True
    assert data["std"] == 0.0
    assert data["anomaly_days"] == 0
    assert all(sample["anomaly"] is False for sample in data["samples"])


def test_anomalies_denied_for_outsider(client, db_session):
    from app.core.security import hash_password
    from app.models import User

    db_session.add(
        User(id="USR-999", username="outsider", real_name="非项目成员", role="safety_officer",
             password_hash=hash_password("BuildWise123!"), is_active=True)
    )
    db_session.commit()

    response = _anomalies(client, user="outsider")
    assert response.status_code == 403
