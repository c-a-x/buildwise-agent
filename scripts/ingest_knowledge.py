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


if __name__ == "__main__":
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(BACKEND))
    subprocess.run([str(PYTHON), "-m", "app.db.seed"], cwd=BACKEND, env=env, check=True)

