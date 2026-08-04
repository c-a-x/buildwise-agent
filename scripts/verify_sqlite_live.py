from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
VENV_PYTHON = BACKEND / ("venv/Scripts/python.exe" if os.name == "nt" else "venv/bin/python")

if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])

sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import func, select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import KnowledgeDocument, Project, User  # noqa: E402


def main() -> None:
    if not settings.database_url.startswith("sqlite:///"):
        raise RuntimeError(f"Expected SQLite DATABASE_URL, got {settings.database_url}")

    database_path = Path(settings.database_url.removeprefix("sqlite:///"))
    if database_path.name == ":memory:" or not database_path.exists():
        raise RuntimeError(f"SQLite file does not exist: {database_path}")

    with SessionLocal() as db:
        user_count = int(db.scalar(select(func.count()).select_from(User)) or 0)
        project_count = int(db.scalar(select(func.count()).select_from(Project)) or 0)
        knowledge_count = int(db.scalar(select(func.count()).select_from(KnowledgeDocument)) or 0)

    if user_count == 0 or project_count == 0:
        raise RuntimeError("SQLite is reachable but seed data is missing; run migrations and app.db.seed")

    with TestClient(app) as client:
        health = client.get("/api/v1/health")
        if health.status_code != 200 or health.json()["data"]["database"]["persistent"] is not True:
            raise RuntimeError(f"Health check did not report persistent SQLite: {health.text}")
        login = client.post("/api/v1/auth/login", json={"username": "manager", "password": "BuildWise123!"})
        if login.status_code != 200:
            raise RuntimeError(f"SQLite-backed login failed: {login.text}")
        headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
        projects = client.get("/api/v1/projects", headers=headers)
        if projects.status_code != 200 or not projects.json()["data"]:
            raise RuntimeError(f"SQLite-backed project query failed: {projects.text}")

    print(f"SQLite live: {database_path} users={user_count} projects={project_count} knowledge={knowledge_count}")


if __name__ == "__main__":
    main()
