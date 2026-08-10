from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import Column, ForeignKey, MetaData, String, Table, create_engine, inspect, text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import CarbonAnalysis, Project, User
from app.core.security import hash_password


BACKEND_DIR = Path(__file__).resolve().parents[1]


def _run_alembic(database_path: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite:///{database_path.as_posix()}"
    return subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=BACKEND_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def _create_legacy_database(
    database_path: Path,
    *,
    with_data: bool,
    alembic_revision: str = "0008_audit_logs",
) -> None:
    engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)

    if with_data:
        with Session(engine) as session:
            user = User(
                id="USR-LEGACY",
                username="legacy-manager",
                password_hash=hash_password("BuildWise123!"),
                real_name="Legacy Manager",
                role="project_manager",
                is_active=True,
            )
            project = Project(
                id="PRJ-LEGACY",
                code="LEGACY-001",
                name="Legacy project",
                address="Legacy address",
                description="",
                status="active",
                manager_user_id=user.id,
            )
            session.add_all([user, project])
            session.flush()
            session.add(
                CarbonAnalysis(
                    id="CAR-LEGACY",
                    project_id=project.id,
                    requested_by=user.id,
                    scope="legacy",
                    is_simulated=True,
                    report_preview="legacy report",
                    factor_version="0.1.0",
                    result_json={"total_emission": 1.0},
                )
            )
            session.commit()

    with engine.begin() as connection:
        connection.execute(text("DROP INDEX ix_agent_runs_module"))

        legacy_metadata = MetaData()
        Table("projects", legacy_metadata, Column("id", String(64), primary_key=True))
        Table("uploads", legacy_metadata, Column("id", String(64), primary_key=True))
        legacy_columns: list[Column[object]] = []
        for column in CarbonAnalysis.__table__.columns:
            if column.name == "requested_by":
                legacy_columns.append(Column("requested_by", String(64), nullable=True))
            else:
                foreign_key = next(iter(column.foreign_keys), None)
                legacy_columns.append(
                    Column(
                        column.name,
                        column.type,
                        ForeignKey(foreign_key.target_fullname) if foreign_key else None,
                        primary_key=column.primary_key,
                        nullable=column.nullable,
                    )
                )
        legacy_table = Table("carbon_analyses_legacy", legacy_metadata, *legacy_columns)
        legacy_table.create(connection)
        connection.execute(
            text(
                "INSERT INTO carbon_analyses_legacy "
                "SELECT id, project_id, source_upload_id, requested_by, area_m2, scope, "
                "total_emission, is_simulated, report_preview, factor_version, result_json, created_at "
                "FROM carbon_analyses"
            )
        )
        connection.execute(text("DROP TABLE carbon_analyses"))
        connection.execute(text("ALTER TABLE carbon_analyses_legacy RENAME TO carbon_analyses"))
        connection.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)")
        )
        connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
            {"revision": alembic_revision},
        )
    engine.dispose()


def _schema_details(database_path: Path) -> tuple[set[str], list[dict[str, object]]]:
    engine = create_engine(f"sqlite:///{database_path}")
    database_inspector = inspect(engine)
    indexes = {index["name"] for index in database_inspector.get_indexes("agent_runs")}
    foreign_keys = database_inspector.get_foreign_keys("carbon_analyses")
    engine.dispose()
    return indexes, foreign_keys


def test_existing_schema_drift_is_detected_before_alignment(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy.db"
    _create_legacy_database(database_path, with_data=False, alembic_revision="0010_green_assessment_env_target")

    result = _run_alembic(database_path, "check")

    output = f"{result.stdout}\n{result.stderr}"
    assert result.returncode != 0
    assert "ix_agent_runs_module" in output
    assert "requested_by" in output


def test_0009_aligns_existing_sqlite_schema_without_data_loss(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy_with_data.db"
    _create_legacy_database(database_path, with_data=True)

    result = _run_alembic(database_path, "upgrade", "head")

    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    indexes, foreign_keys = _schema_details(database_path)
    assert "ix_agent_runs_module" in indexes
    assert any(
        set(foreign_key["constrained_columns"] or []) == {"requested_by"}
        and foreign_key["referred_table"] == "users"
        and set(foreign_key["referred_columns"] or []) == {"id"}
        for foreign_key in foreign_keys
    )

    engine = create_engine(f"sqlite:///{database_path}")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM users")).scalar_one() == 1
        assert connection.execute(text("SELECT COUNT(*) FROM projects")).scalar_one() == 1
        assert connection.execute(text("SELECT id FROM carbon_analyses")).scalar_one() == "CAR-LEGACY"
    engine.dispose()

    check_result = _run_alembic(database_path, "check")
    assert check_result.returncode == 0, f"{check_result.stdout}\n{check_result.stderr}"


def test_empty_sqlite_upgrade_reaches_0010_and_metadata_is_aligned(tmp_path: Path) -> None:
    database_path = tmp_path / "empty.db"

    upgrade_result = _run_alembic(database_path, "upgrade", "head")

    assert upgrade_result.returncode == 0, f"{upgrade_result.stdout}\n{upgrade_result.stderr}"
    engine = create_engine(f"sqlite:///{database_path}")
    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    engine.dispose()
    assert revision == "0010_green_assessment_env_target"

    indexes, foreign_keys = _schema_details(database_path)
    assert "ix_agent_runs_module" in indexes
    assert any(
        set(foreign_key["constrained_columns"] or []) == {"requested_by"}
        and foreign_key["referred_table"] == "users"
        for foreign_key in foreign_keys
    )
    check_result = _run_alembic(database_path, "check")
    assert check_result.returncode == 0, f"{check_result.stdout}\n{check_result.stderr}"
