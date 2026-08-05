from __future__ import annotations

import json
from io import BytesIO

from app.core.config import settings
from app.models import CarbonAnalysis
from app.providers.carbon import load_factor_library

ANALYZE_PAYLOAD = {
    "project_id": "PRJ-001",
    "area_m2": 8500,
    "scope": "一期主体结构施工阶段",
    "materials": [
        {"code": "CONCRETE_C30", "name": "C30商品混凝土", "quantity": 860, "unit": "m3"},
        {"code": "REBAR_HOT_ROLLED", "name": "热轧钢筋", "quantity": 120, "unit": "t"},
    ],
    "transport": [{"code": "TRUCK_46T_DIESEL", "name": "重型柴油货车(46t)", "quantity": 51600, "unit": "t·km"}],
    "energy": [{"code": "GRID_ELEC", "name": "外购电力", "quantity": 180000, "unit": "kWh"}],
}


def test_load_factor_library_from_temp(tmp_path):
    factor_file = tmp_path / "factors.json"
    factor_file.write_text(
        json.dumps(
            {
                "version": "test-1",
                "materials": [{"code": "A", "name": "A材料", "unit": "t", "factor": 1.5, "factor_unit": "tCO2e/t", "source": "测试", "verified": True}],
                "energy": [],
                "transport": [],
            }
        ),
        encoding="utf-8",
    )
    library = load_factor_library(factor_file)
    assert library.version == "test-1"
    assert library.load_error == ""
    assert library.get("A").factor == 1.5
    assert all(factor.verified for factor in library.factors)


def test_shipped_factor_library_has_verified_grid_factor():
    library = load_factor_library(settings.green_factors_path)
    assert library.load_error == ""
    assert library.version == "0.1.0"
    assert library.get("CONCRETE_C30") is not None
    grid = library.get("GRID_ELEC")
    assert grid is not None
    assert grid.verified is True
    assert grid.factor == 0.0005703


def test_status_available(client):
    from tests.conftest import login

    response = client.get("/api/v1/green/status", headers=login(client, "manager"))
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "available"


def test_factors_endpoint(client):
    from tests.conftest import login

    response = client.get("/api/v1/green/factors", headers=login(client, "manager"))
    assert response.status_code == 200
    factors = response.json()["data"]
    assert len(factors) > 0
    grid = next(factor for factor in factors if factor["code"] == "GRID_ELEC")
    assert grid["verified"] is True


def test_analyze_computes_stages_and_persists(client, db_session):
    from tests.conftest import login

    response = client.post("/api/v1/green/analyze", json=ANALYZE_PAYLOAD, headers=login(client, "manager"))
    assert response.status_code == 200
    data = response.json()["data"]

    # C30 860m3*0.295 + 钢筋 120t*2.34 = 534.5；运输 51600*0.000057≈2.9412；电力 180000*0.0005703≈102.654
    assert data["total_emission"] == round(860 * 0.295 + 120 * 2.34 + 51600 * 0.000057 + 180000 * 0.0005703, 4)
    assert data["intensity"] == round(data["total_emission"] / 8500, 4)
    by_stage = {stage["stage"]: stage for stage in data["stages"]}
    assert by_stage["A1-A3"]["emission"] == round(534.5, 4)
    assert by_stage["A4"]["emission"] == round(51600 * 0.000057, 4)
    assert by_stage["A5"]["emission"] == round(180000 * 0.0005703, 4)
    assert len(data["items"]) == 4
    assert data["has_unverified_factors"] is True  # 演示因子未核证
    assert data["is_simulated"] is True
    assert data["factor_warnings"] == []
    assert "总排放" in data["report_preview"]
    assert len(data["suggestions"]) > 0

    row = db_session.query(CarbonAnalysis).filter(CarbonAnalysis.id == data["analysis_id"]).one()
    assert row.requested_by == "USR-001"
    assert row.total_emission == data["total_emission"]
    assert row.is_simulated is True


def test_analyze_missing_factor_warns_not_errors(client):
    from tests.conftest import login

    payload = {
        "project_id": "PRJ-001",
        "materials": [{"code": "UNKNOWN_MATERIAL", "name": "神秘材料", "quantity": 10, "unit": "t"}],
        "transport": [],
        "energy": [],
    }
    response = client.post("/api/v1/green/analyze", json=payload, headers=login(client, "manager"))
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_emission"] == 0.0
    assert data["items"][0]["factor_missing"] is True
    assert len(data["factor_warnings"]) >= 1
    assert data["is_simulated"] is True


def test_analyses_list_and_detail_roundtrip(client):
    from tests.conftest import login

    headers = login(client, "manager")
    created = client.post("/api/v1/green/analyze", json=ANALYZE_PAYLOAD, headers=headers).json()["data"]

    listing = client.get("/api/v1/green/analyses", headers=headers).json()["data"]
    assert any(item["analysis_id"] == created["analysis_id"] for item in listing)

    detail = client.get(f"/api/v1/green/analyses/{created['analysis_id']}", headers=headers).json()["data"]
    assert detail["total_emission"] == created["total_emission"]
    assert detail["project_name"] == "测试演示项目"
    assert len(detail["stages"]) == 3


def test_analyses_filter_by_project(client, db_session):
    from tests.conftest import login

    headers = login(client, "manager")
    client.post("/api/v1/green/analyze", json=ANALYZE_PAYLOAD, headers=headers)
    listing = client.get("/api/v1/green/analyses?project_id=PRJ-001", headers=headers).json()["data"]
    assert all(item["project_id"] == "PRJ-001" for item in listing)


def test_report_download_generates_docx(client):
    from docx import Document
    from tests.conftest import login

    headers = login(client, "manager")
    created = client.post("/api/v1/green/analyze", json=ANALYZE_PAYLOAD, headers=headers).json()["data"]

    response = client.get(f"/api/v1/green/analyses/{created['analysis_id']}/report", headers=headers)
    assert response.status_code == 200
    assert "wordprocessingml" in response.headers["content-type"]
    assert "filename" in response.headers["content-disposition"]
    assert response.content[:2] == b"PK"  # docx 是 zip 容器

    document = Document(BytesIO(response.content))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "建筑碳排放核算报告" in text
    assert "A1-A3" in text
    assert "减排建议" in text


def test_report_download_denied_for_other_project(client, db_session):
    from app.core.security import hash_password
    from app.models import User
    from tests.conftest import login

    headers = login(client, "manager")
    created = client.post("/api/v1/green/analyze", json=ANALYZE_PAYLOAD, headers=headers).json()["data"]

    db_session.add(User(id="USR-999", username="outsider", real_name="非项目成员", role="safety_officer", password_hash=hash_password("BuildWise123!"), is_active=True))
    db_session.commit()
    outsider = login(client, "outsider")
    response = client.get(f"/api/v1/green/analyses/{created['analysis_id']}/report", headers=outsider)
    assert response.status_code == 403


# ---------- benchmark ----------

def _create_benchmark_project(db, project_id, name, manager="USR-001"):
    from app.models import Project, ProjectMember

    db.add(Project(id=project_id, code=f"CODE-{project_id}", name=name, address="测试地址", description="", status="active", manager_user_id=manager))
    db.add(ProjectMember(project_id=project_id, user_id=manager, project_role="project_manager"))
    db.flush()


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


def _benchmark(client, project_id=None):
    from tests.conftest import login

    url = "/api/v1/green/benchmark" + (f"?project_id={project_id}" if project_id else "")
    return client.get(url, headers=login(client, "manager")).json()["data"]


def test_benchmark_single_project_degraded(client, db_session):
    from datetime import datetime, timezone

    _insert_analysis(db_session, "CAR-BM-001", "PRJ-001", 1000, 10000, datetime(2026, 8, 1, tzinfo=timezone.utc))
    db_session.commit()

    data = _benchmark(client)
    assert data["available"] is False
    assert "样本不足" in data["reason"]


def test_benchmark_ranks_projects_by_intensity(client, db_session):
    from datetime import datetime, timezone

    _create_benchmark_project(db_session, "PRJ-002", "第二项目")
    _insert_analysis(db_session, "CAR-BM-001", "PRJ-001", 1000, 10000, datetime(2026, 8, 1, tzinfo=timezone.utc))  # 0.1
    _insert_analysis(db_session, "CAR-BM-002", "PRJ-002", 500, 10000, datetime(2026, 8, 1, tzinfo=timezone.utc))  # 0.05
    db_session.commit()

    data = _benchmark(client)
    assert data["available"] is True
    assert data["count"] == 2
    assert data["items"][0]["project_id"] == "PRJ-002"  # 低强度 rank 1
    assert data["items"][0]["z"] < 0
    assert data["items"][0]["better_than_pct"] == 50.0
    assert data["items"][1]["project_id"] == "PRJ-001"
    assert data["items"][1]["better_than_pct"] == 0.0


def test_benchmark_highlights_current_project(client, db_session):
    from datetime import datetime, timezone

    _create_benchmark_project(db_session, "PRJ-002", "第二项目")
    _insert_analysis(db_session, "CAR-BM-001", "PRJ-001", 1000, 10000, datetime(2026, 8, 1, tzinfo=timezone.utc))
    _insert_analysis(db_session, "CAR-BM-002", "PRJ-002", 500, 10000, datetime(2026, 8, 1, tzinfo=timezone.utc))
    db_session.commit()

    data = _benchmark(client, "PRJ-002")
    assert data["current"]["project_id"] == "PRJ-002"
    assert data["current"]["rank"] == 1


def test_benchmark_ignores_analyses_without_area(client, db_session):
    from datetime import datetime, timezone

    _create_benchmark_project(db_session, "PRJ-002", "第二项目")
    _create_benchmark_project(db_session, "PRJ-003", "第三项目")
    _insert_analysis(db_session, "CAR-BM-001", "PRJ-001", 1000, None, datetime(2026, 8, 1, tzinfo=timezone.utc))  # 无面积，排除
    _insert_analysis(db_session, "CAR-BM-002", "PRJ-002", 500, 10000, datetime(2026, 8, 1, tzinfo=timezone.utc))
    _insert_analysis(db_session, "CAR-BM-003", "PRJ-003", 1000, 10000, datetime(2026, 8, 1, tzinfo=timezone.utc))
    db_session.commit()

    data = _benchmark(client)
    assert data["count"] == 2
    assert all(item["project_id"] != "PRJ-001" for item in data["items"])


def test_benchmark_uses_latest_analysis_per_project(client, db_session):
    from datetime import datetime, timezone

    _create_benchmark_project(db_session, "PRJ-002", "第二项目")
    _insert_analysis(db_session, "CAR-BM-OLD", "PRJ-001", 10000, 10000, datetime(2026, 7, 1, tzinfo=timezone.utc))  # 旧 1.0
    _insert_analysis(db_session, "CAR-BM-NEW", "PRJ-001", 1000, 10000, datetime(2026, 8, 1, tzinfo=timezone.utc))  # 新 0.1
    _insert_analysis(db_session, "CAR-BM-002", "PRJ-002", 500, 10000, datetime(2026, 8, 1, tzinfo=timezone.utc))
    db_session.commit()

    data = _benchmark(client)
    prj001 = next(item for item in data["items"] if item["project_id"] == "PRJ-001")
    assert prj001["intensity"] == 0.1


def test_benchmark_denied_for_outsider(client, db_session):
    from app.core.security import hash_password
    from app.models import User
    from tests.conftest import login

    db_session.add(User(id="USR-999", username="outsider", real_name="非项目成员", role="safety_officer", password_hash=hash_password("BuildWise123!"), is_active=True))
    db_session.commit()

    response = client.get("/api/v1/green/benchmark?project_id=PRJ-001", headers=login(client, "outsider"))
    assert response.status_code == 403
