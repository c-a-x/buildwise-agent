#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

if [[ -x "$BACKEND/venv/bin/python" ]]; then
  PYTHON="$BACKEND/venv/bin/python"
else
  PYTHON="python3"
fi

(cd "$BACKEND" && "$PYTHON" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000) &
BACKEND_PID=$!
trap 'kill "$BACKEND_PID" 2>/dev/null || true' EXIT INT TERM

cd "$FRONTEND"
npm run dev -- --host 0.0.0.0

