# 筑智共生 · BuildWise AI Agent

当前冻结版本：`v0.2.0-docker-ready`。

BuildWise 是面向施工现场的安全运营工作台：上传现场图片后，五个离线 Agent 依次完成安全识别、规范检索、工单草稿、工友提醒和日报预览；正式工单必须经过人工确认，并按 `pending → in_progress → pending_review → closed` 流转。

默认配置不需要外部 API Key，数据库使用真实 SQLite 文件，适合离线演示和自动化验收。前端不会直接连接数据库，而是通过 FastAPI → SQLAlchemy → SQLite 读取和写入数据。规范检索默认使用本地关键词 Provider；Chroma 模式使用真实持久化向量 collection，但仍使用离线可重复 embedding，不依赖外部文本大模型。

## 环境要求

- Python 3.11 或更高版本；
- Node.js 22 或更高版本、npm；
- Docker Engine 和 Docker Compose v2（仅 Docker 启动需要）；
- Windows 使用 PowerShell 5+，Unix 使用 Bash。

## 本地启动

### Windows PowerShell

首次安装依赖并初始化数据库：

```powershell
cd E:\cc项目\buildwise-agent
py -3.11 -m venv backend\venv
backend\venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
cd backend
..\backend\venv\Scripts\python.exe -m alembic upgrade head
..\backend\venv\Scripts\python.exe -m app.db.seed
cd ..\frontend
npm ci
```

分别启动后端和前端：

```powershell
cd E:\cc项目\buildwise-agent\backend
..\backend\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

```powershell
cd E:\cc项目\buildwise-agent\frontend
npm run dev -- --host 0.0.0.0
```

也可以一键运行（会先执行迁移和种子，后端日志写入 `backend/storage/logs/dev-backend.log`）：

```powershell
cd E:\cc项目\buildwise-agent
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dev.ps1
```

### macOS / Linux

```bash
cd /path/to/buildwise-agent
python3.11 -m venv backend/venv
backend/venv/bin/python -m pip install -e 'backend[dev]'
(cd backend && ../backend/venv/bin/python -m alembic upgrade head && ../backend/venv/bin/python -m app.db.seed)
cd frontend
npm ci
```

分别启动：

```bash
(cd backend && ../backend/venv/bin/python -m uvicorn app.main:app --reload --port 8000)
cd frontend && npm run dev -- --host 0.0.0.0
```

或运行一键脚本：

```bash
./scripts/dev.sh
```

本地地址：

- 前端：<http://localhost:5173>
- Swagger：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/api/v1/health>

## SQLite 数据库

默认数据库文件为 `backend/storage/buildwise.db`，启动脚本会先执行 Alembic 迁移和种子，之后前端所有登录、项目、分析、工单和日报请求都通过后端读写该文件。`backend/tests/` 中的测试夹具使用内存 SQLite 以隔离测试，不代表开发运行时使用假数据库。

检查当前真实数据库是否可读、种子数据是否存在以及前后端 API 是否能读到项目：

```powershell
cd E:\cc项目\buildwise-agent
python scripts\verify_sqlite_live.py
```

可以通过 `backend/.env` 的 `DATABASE_URL` 指向其他 SQLite 文件；相对 SQLite 路径会固定按 `backend/` 目录解析，不会随启动命令所在目录漂移。

## Docker Compose

```powershell
docker compose config
docker compose --progress plain build
docker compose up -d
```

容器启动时会执行 Alembic 迁移和演示种子。访问 <http://localhost:8080>；前端 Nginx 将 `/api/` 和 `/storage/` 反向代理到后端，SQLite 数据保存在 `buildwise-storage`，Chroma 数据保存在独立的 `buildwise-chroma` Compose volume 中。

保留 SQLite volume 的无缓存重建：

```powershell
docker compose down
docker compose pull
docker compose build --no-cache
docker compose up -d
```

执行容器内迁移、种子和真实 HTTP 闭环验收：

```powershell
docker compose exec -T backend alembic upgrade head
docker compose exec -T backend python -m app.db.seed
backend\venv\Scripts\python.exe scripts\e2e_docker.py
```

`scripts/e2e_docker.py` 默认访问 `http://localhost:8000/api/v1`，覆盖登录、项目列表、图片上传、五 Agent、工单确认与状态流转、日报、知识检索和 `normal` 场景；上传文件通过 `http://localhost:8080/storage/` 再验证一次 Nginx 代理。前端镜像使用 Node 22 Alpine 构建，npm 源可通过 `NPM_REGISTRY` build arg 覆盖；项目不依赖项目目录内的 npm 或原生构建缓存，`node_modules`、`dist`、虚拟环境和运行时目录均不会进入 Git 或 Docker 构建上下文。

停止并删除容器（保留 volume）：

```powershell
docker compose down
```

如需连同 SQLite 数据卷一起清理（会删除容器数据）：

```powershell
docker compose down -v
```

## Provider 切换

复制 `backend/.env.example` 为 `backend/.env`，默认离线配置如下：

```env
VISION_PROVIDER=mock
RETRIEVAL_PROVIDER=local_keyword
CHROMA_DIR=storage/chroma
CHROMA_MIN_SCORE=0.42
TEXT_PROVIDER=template
```

默认模式不读取外部密钥，响应中的 `is_simulated` 会明确为 `true`。真实 Provider 需要人工准备并验证：

- `VISION_PROVIDER=ultralytics`：设置 `VISION_MODEL_PATH`，并安装/许可对应 YOLO 模型依赖；
- `VISION_PROVIDER=safety_hybrid`：十类安全目标混合检测（YOLO + 可选 LLM 隐患分析），详见下节「十类视觉检测」；
- `RETRIEVAL_PROVIDER=chroma`：使用 `CHROMA_DIR` 下的真实持久化 Chroma collection；先按下方命令导入已授权条款；
- `TEXT_PROVIDER=openai_compatible`：同时设置 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`；
- 未配置必需参数时接口返回明确的 `PROVIDER_NOT_CONFIGURED`，不会静默退回模拟结果。

不要把真实 API Key 写入仓库、镜像或文档。真实模型的许可、网络、成本和生产密钥由部署方负责。

## 十类视觉检测（safety_hybrid）

视觉识别可切换为 `safety_hybrid` 混合 Provider：YOLO 目标检测识别 10 类施工安全目标，可选叠加 LLM 隐患分析。

- **10 类**：Hardhat / Mask / NO-Hardhat / NO-Mask / NO-Safety Vest / Person / Safety Cone / Safety Vest / machinery / vehicle；
- **违规映射**：NO-Hardhat → 未佩戴安全帽（高危）、NO-Mask → 未佩戴口罩（中危）、NO-Safety Vest → 未穿反光安全背心（中危），均会生成整改工单草稿；已合规佩戴（Hardhat/Mask/Safety Vest/Safety Cone）不生成隐患；
- **模型**：`backend/storage/models/yolov8n-10cls.pt`（在 [Construction Site Safety Image Dataset](https://www.kaggle.com/datasets/snehilsanyal/construction-site-safety-image-dataset-roboflow) 上训练的 10 类 YOLOv8n）。模型为运行时数据（已被 `.gitignore` 排除），需按下方说明放置；
- **检测图**：前端在浏览器内基于检测框坐标叠加绘制，切换「原图 / 检测图」即可查看，后端无需额外标注文件。

配置（`backend/.env`）：

```env
VISION_PROVIDER=safety_hybrid
YOLO_MODEL_PATH=storage/models/yolov8n-10cls.pt
YOLO_CONF_THRESHOLD=0.5

# LLM 隐患分析（可选；不配置或调用失败时自动降级为纯 YOLO）
VISION_LLM_PROVIDER=off          # claude_cli | doubao | off
# VISION_LLM_PROVIDER=doubao 时同时设置：
# LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
# LLM_API_KEY=你的key
# LLM_MODEL=doubao-seed-2-0-mini-260215
```

**降级规则**：YOLO 模型缺失、加载失败或未安装 `backend[vision]` 依赖时，自动降级为模拟结果并显式标记 `is_simulated=true`，不会中断请求；`VISION_LLM_PROVIDER=off` 或 LLM 调用失败时仅保留 YOLO 检测（`is_simulated=false`，仍为真实检测）。

**模型放置**：模型文件是运行期数据、不入 Git。可从数据集训练产物中复制 `results_yolov8n_100e/kaggle/working/runs/detect/train/weights/best.pt` 到 `backend/storage/models/yolov8n-10cls.pt`，或用 ultralytics 在同一 10 类数据集上自行训练并替换。

## Chroma 规范知识库

只导入来源明确且已获授权的规范文件；仓库不提供来源不明的国家标准文件，也不虚构标准编号或条款。支持三种输入：

- JSON：根节点可以是条款数组，也可以是包含 `clauses`、`articles`、`documents` 或 `items` 的对象。每条建议提供 `id`/`document_id`、`source`、`title`、`article`、`category`、`content`、`version`、`effective_date` 和 `metadata`；旧版演示 JSON 的 `hazard_types`、`keywords` 也会保留；
- PDF/DOCX：必须通过命令行提供已授权的 `--source`、`--title`、`--category`。正文必须包含显式条款标题（例如 `第12条`、`第4.3.1条`、`Article 12`）；没有条款号会拒绝导入，不会生成“全文”条款；
- 条款正文、条款号和来源会一并保存，扩展 metadata 以 JSON 保留。

本地导入命令（先执行 Alembic 迁移）：

```powershell
cd E:\cc项目\buildwise-agent
backend\venv\Scripts\python.exe scripts\ingest_knowledge.py --input data_demo\standards\safety_standards.json
backend\venv\Scripts\python.exe scripts\ingest_knowledge.py --input path\to\authorized.pdf --source "已授权来源" --title "文档标题" --category "施工安全" --version "2026" --effective-date 2026-01-01
```

重复运行会按稳定条款 ID 增量 upsert，并报告 `created`、`updated`、`skipped`、`deleted` 和条款总数。重建或清空后重建：

```powershell
backend\venv\Scripts\python.exe scripts\ingest_knowledge.py --rebuild
backend\venv\Scripts\python.exe scripts\ingest_knowledge.py --clear --rebuild
```

切换 Provider：

```powershell
$env:RETRIEVAL_PROVIDER = "chroma"
docker compose up -d --build
docker compose exec -T backend python scripts/ingest_knowledge.py --input data_demo/standards/safety_standards.json --rebuild

# 恢复默认离线关键词检索
$env:RETRIEVAL_PROVIDER = "local_keyword"
```

索引状态可通过页面“规范知识库”查看，也可调用 `GET /api/v1/knowledge/index/status`。检索接口返回来源、条款、正文、相似度和 metadata；无命中返回空数组。`buildwise-chroma` volume 可以随容器重启保留索引；`docker compose down -v` 会删除它以及 SQLite volume，请仅在明确需要清理开发数据时使用。

## 主 Demo

完整步骤见 [`docs/demo-script.md`](docs/demo-script.md)：

1. 使用 `safety / BuildWise123!` 登录；
2. 打开”安全分析”，点击任一内置示例图（或上传现场照片）；
3. 点击”开始安全分析”，在结果区切换「原图 / 检测图」查看检测框，并查看隐患、置信度、规范证据、五 Agent trace 和工单草稿；
4. 点击“确认创建正式工单”；
5. 在工单详情依次推进到“整改中”“待复查”，填写复查备注后关闭；
6. 使用 `manager / BuildWise123!` 验证项目经理权限，并在“日报中心”刷新当天日报；
7. 在“安全历史”打开任务链接，验证刷新后草稿、提醒和日报预览仍然存在。

也可执行自动化验收：

```powershell
cd E:\cc项目\buildwise-agent
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\test_runbooks.ps1
```

## 演示账号

| 账号 | 密码 | 角色 |
| --- | --- | --- |
| `manager` | `BuildWise123!` | 项目经理 |
| `safety` | `BuildWise123!` | 安全员 |
| `quality` | `BuildWise123!` | 质检员 |
| `worker` | `BuildWise123!` | 工人 |

## 验证命令

```powershell
cd E:\cc项目\buildwise-agent\backend
..\backend\venv\Scripts\python.exe -m pytest -q
..\backend\venv\Scripts\python.exe -m alembic upgrade head

cd ..\frontend
npm run test:unit -- --run
npm run type-check
npm run build
```

## 常见问题

### 8000 或 5173 端口被占用

停止占用端口的进程，或分别将 Uvicorn 的 `--port` 和 Vite 的 `--host/--port` 改为未占用端口；同时更新 `frontend/.env` 的 `VITE_API_BASE_URL` 和后端 `CORS_ORIGINS`。

### Alembic 迁移失败或数据库结构过旧

确认命令在 `backend/` 目录执行，并使用项目虚拟环境：`..\backend\venv\Scripts\python.exe -m alembic upgrade head`。开发环境需要重建数据库时，先备份 `backend/storage/buildwise.db`，再按项目允许的方式清理后重新迁移和种子。

### 浏览器提示 CORS

检查 `backend/.env` 的 `CORS_ORIGINS` 是否包含实际前端 origin（例如 `http://localhost:5173`），修改后重启后端；Docker 模式应包含 `http://localhost:8080`。

### Provider 配置错误

先恢复 `VISION_PROVIDER=mock`、`RETRIEVAL_PROVIDER=local_keyword`、`TEXT_PROVIDER=template` 验证离线闭环。切换真实 Provider 时逐项检查模型路径、Chroma 目录和三个 LLM 配置，接口错误码会指出缺失配置。

### 已知构建和运行提示

- `glob@10.5.0` 是 `@vue/test-utils → js-beautify` 带入的开发依赖，当前不进入生产镜像且不影响运行时；待上游依赖链提供兼容升级后再处理，不在此处强制覆盖跨主版本依赖。
- Nginx 的 epoll、worker 启动和优雅退出 notice 属于容器生命周期日志，不是应用错误。
- Node 22 已满足前端锁定的 Vite、Rolldown、OxFMT 和原生插件引擎要求；干净构建不应出现 Node 20 的 EBADENGINE 或 WASI 实验性提示。

### 图片无法上传或没有检测图

只支持 JPEG、PNG、WEBP，大小上限由 `MAX_UPLOAD_MB` 控制。确认 `backend/storage/uploads` 可写；检测图由前端在浏览器内叠加检测框绘制，切换「原图 / 检测图」查看，无需后端标注文件。

## 页面与目录

页面和路由覆盖登录、注册、找回密码、仪表盘、项目管理、安全分析、安全历史、整改工单、工单详情、工友助手、日报及历史、质量占位、绿色占位、知识库、个人资料、系统设置，以及 403/404 页面。

- `frontend/`：Vue 3 + TypeScript + Pinia + Vue Router；
- `backend/`：FastAPI + Pydantic + SQLAlchemy + Alembic + LangGraph；
- `data_demo/`：规范数据、演示图片、示例日报和材料数据；
- `scripts/`：本地启动、种子、知识导入、演示图片和 runbook 校验；
- `docs/`：产品、架构、API、数据库、算法、部署和演示文档。

## 能力边界

- 视觉识别可切换为 `safety_hybrid` 十类真实 YOLO 检测（未佩戴安全帽/未戴口罩/未穿安全背心/人/机械/车辆等）；模型未配置或加载失败时降级为模拟结果并显式标记 `is_simulated=true`；文本生成仍为本地模板 Provider；
- `RETRIEVAL_PROVIDER=local_keyword` 是离线关键词能力，`chroma` 是本轮接入的真实持久化向量检索投影；
- 未命中本地规范时不编造条款，证据不足会提示人工补充；
- AI 只能生成工单草稿，人工确认后才写入正式工单；
- 日报核心数字来自 SQL 聚合，日报文案可由模板或真实文本 Provider 生成；
- 质量和绿色施工提供正式页面、状态接口和数据结构，尚未接入真实巡检或碳排数据源；
- 生产环境仍需更换 `SECRET_KEY`、使用 PostgreSQL/对象存储、限制 CORS、启用 HTTPS、集中日志和速率限制。

## 后续路线

- 为视觉识别接入 LLM 隐患分析（豆包/Claude CLI），补齐 H1-H10 分级与规范条款引用；
- 接入 OpenAI-compatible 文本 Provider、语音提醒和权限审计；
- 为 `QualityAgent` 接入真实质量巡检数据源；
- 为 `GreenAgent` 接入真实材料和碳排数据源；
- 面向生产环境迁移 PostgreSQL、对象存储、HTTPS、集中日志和速率限制。
