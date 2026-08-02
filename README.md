# 筑智共生 · BuildWise AI Agent

面向施工现场的安全运营工作台原型：通过图片分析串起风险识别、规范证据、人工确认工单、整改状态和日报统计。项目默认离线可运行，适合产品演示和后续接入真实模型。

## 快速启动

### Windows PowerShell

```powershell
cd E:\cc项目\buildwise-agent
python -m venv backend\venv
backend\venv\Scripts\python.exe -m pip install -e "backend[dev]"
cd backend
..\backend\venv\Scripts\python.exe -m alembic upgrade head
..\backend\venv\Scripts\python.exe -m app.db.seed
cd ..\frontend
npm install
npm run dev
```

另开一个终端启动后端：

```powershell
cd E:\cc项目\buildwise-agent\backend
..\backend\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

也可以运行 `powershell -ExecutionPolicy Bypass -File scripts\dev.ps1`，它会启动后端并以前台方式启动 Vite。

访问：

- 前端：<http://localhost:5173>
- API 文档：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/health>

### Docker Compose

```powershell
docker compose up --build
```

访问 <http://localhost:8080>。

## 验证命令

```powershell
cd backend
python -m pytest -q
python -m alembic upgrade head

cd ..\frontend
npm run type-check
npm run build
```

根目录也提供 `Makefile`、`scripts\seed_demo.py`、`scripts\ingest_knowledge.py` 和 `scripts\dev.ps1` / `scripts\dev.sh`。

## 页面与路由

已实现的核心页面包括：登录、注册、找回密码、仪表盘、项目管理、安全分析、安全历史、工单中心、工单详情、工人关怀、日报中心、日报历史、质量管理占位、绿色施工占位、知识库、个人资料、系统设置，以及 403/404 错误页。

## 演示账号

| 账号 | 密码 | 角色 |
| --- | --- | --- |
| `manager` | `BuildWise123!` | 项目经理 |
| `safety` | `BuildWise123!` | 安全员 |
| `quality` | `BuildWise123!` | 质检员 |
| `worker` | `BuildWise123!` | 工人 |

## 能力边界

- 默认视觉识别、规范检索和文本生成均为本地 Provider；返回数据会明确标记 `is_simulated=true`。
- 真实视觉模型可通过 `backend/app/providers/vision/` 的接口替换；真实文本/向量 Provider 可通过对应目录接入。
- 未命中本地规范时不编造条款。
- AI 仅生成工单草稿，只有人工确认才会创建正式工单。
- 质量和绿色施工当前提供正式页面、状态接口和数据结构，尚未接入真实巡检或碳排数据源。

## 目录

- `frontend/`：Vue 3 + TypeScript + Pinia + Vue Router；
- `backend/`：FastAPI + SQLAlchemy + Alembic + pytest；
- `data_demo/`：安全规范、音频说明、示例日报和材料数据；
- `docs/`：规格、架构、API、数据库、算法和演示文档；
- `design-system/buildwise-ai-agent/MASTER.md`：按 UI/UX 规范生成并持久化的设计系统。
