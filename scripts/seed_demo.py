from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
PYTHON = BACKEND / "venv" / "Scripts" / "python.exe"
if not PYTHON.exists():
    PYTHON = Path(sys.executable)


def run(module: str) -> None:
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(BACKEND))
    subprocess.run([str(PYTHON), "-m", module], cwd=BACKEND, env=env, check=True)


if __name__ == "__main__":
    run("app.db.init_db")
    run("app.db.seed")

