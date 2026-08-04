from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import BACKEND_DIR, settings
from app.main import app


def test_default_sqlite_database_url_resolves_to_backend_storage_file():
    assert settings.database_url.startswith("sqlite:///")
    database_path = Path(settings.database_url.removeprefix("sqlite:///"))
    assert database_path.is_absolute()
    assert database_path == BACKEND_DIR / "storage" / "buildwise.db"


def test_live_health_endpoint_reports_connected_sqlite_database():
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    database = response.json()["data"]["database"]
    assert database["status"] == "connected"
    assert database["dialect"] == "sqlite"
    assert database["persistent"] is True
