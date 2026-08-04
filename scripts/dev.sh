#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
LOG_DIR="$BACKEND/storage/logs"
BACKEND_LOG="$LOG_DIR/dev-backend.log"

if [[ -x "$BACKEND/venv/bin/python" ]]; then
  PYTHON="$BACKEND/venv/bin/python"
elif [[ -x "$BACKEND/venv/Scripts/python.exe" ]]; then
  PYTHON="$BACKEND/venv/Scripts/python.exe"
else
  echo "未找到 backend/venv Python，请先按 README 安装依赖。" >&2
  exit 1
fi

mkdir -p "$LOG_DIR"
(cd "$BACKEND" && "$PYTHON" -m alembic upgrade head)
(cd "$BACKEND" && "$PYTHON" -m app.db.seed)

(cd "$BACKEND" && exec "$PYTHON" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 >>"$BACKEND_LOG" 2>&1) &
BACKEND_PID=$!

cleanup() {
  if kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID"
    if wait "$BACKEND_PID" 2>/dev/null; then
      :
    else
      :
    fi
  fi
}
trap cleanup EXIT INT TERM

sleep 2
if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
  echo "后端进程启动后立即退出，日志：$BACKEND_LOG" >&2
  cat "$BACKEND_LOG" >&2
  exit 1
fi

cd "$FRONTEND"
if npm run dev -- --host 0.0.0.0; then
  FRONTEND_STATUS=0
else
  FRONTEND_STATUS=$?
fi

if (( FRONTEND_STATUS != 0 )); then
  echo "前端开发服务器退出，状态码：$FRONTEND_STATUS" >&2
  exit "$FRONTEND_STATUS"
fi

if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
  echo "后端进程已在前端正常退出前结束，日志：$BACKEND_LOG" >&2
  cat "$BACKEND_LOG" >&2
  exit 1
fi
