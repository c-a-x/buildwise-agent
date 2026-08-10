from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import BACKEND_DIR, _path_from_env, settings
from app.main import app


def test_default_sqlite_database_url_resolves_to_backend_storage_file():
    assert settings.database_url.startswith("sqlite:///")
    database_path = Path(settings.database_url.removeprefix("sqlite:///"))
    assert database_path.is_absolute()
    assert database_path == BACKEND_DIR / "storage" / "buildwise.db"


def test_path_from_env_resolves_absolute_and_backend_relative_paths(tmp_path):
    relative = _path_from_env("storage/uploads", "storage/uploads")
    absolute_input = tmp_path / "uploads"
    absolute = _path_from_env(str(absolute_input), "storage/uploads")

    assert relative == (BACKEND_DIR / "storage" / "uploads").resolve()
    assert absolute == absolute_input.resolve()


def test_live_health_endpoint_reports_connected_sqlite_database():
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    database = response.json()["data"]["database"]
    assert database["status"] == "connected"
    assert database["dialect"] == "sqlite"
    assert database["persistent"] is True
