from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _run_ingest(input_path: Path, env: dict[str, str], *arguments: str) -> dict[str, object]:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "ingest_knowledge.py"), "--input", str(input_path), *arguments],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_ingest_command_is_incremental_and_rebuildable(tmp_path: Path) -> None:
    input_path = tmp_path / "authorized.json"
    input_path.write_text(
        json.dumps(
            [
                {
                    "id": "DOC-CMD-001",
                    "title": "授权安全制度",
                    "source": "授权项目制度",
                    "article": "第12条",
                    "category": "个人防护",
                    "version": "2026",
                    "content": "进入现场必须佩戴安全帽。",
                    "hazard_types": ["no_helmet"],
                    "keywords": ["安全帽"],
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    database_path = tmp_path / "buildwise.db"
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONPATH": str(ROOT / "backend"),
            "RETRIEVAL_PROVIDER": "chroma",
            "CHROMA_DIR": str(tmp_path / "chroma"),
            "DATABASE_URL": f"sqlite:///{database_path.as_posix()}",
            "KNOWLEDGE_JSON_PATH": str(input_path),
        }
    )

    first = _run_ingest(input_path, environment, "--rebuild")
    second = _run_ingest(input_path, environment)
    rebuilt = _run_ingest(input_path, environment, "--clear", "--rebuild")

    assert first["clause_count"] == 1
    assert second["clause_count"] == 1
    assert second["skipped"] == 1
    assert rebuilt["clause_count"] == 1
