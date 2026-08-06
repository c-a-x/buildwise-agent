# 筑智共生 · BuildWise AI Agent

当前冻结版本：`v0.2.0-docker-ready`。

BuildWise 是面向施工现场的安全运营工作台，覆盖**安全分析、实时监控、质量巡检、工友助手、绿色碳排核算、知识库问答与统计分析**：安全分析上传现场图片后，五个离线 Agent 依次完成安全识别、规范检索、工单草稿、工友提醒和日报预览；正式工单必须经过人工确认，并按 `pending → in_progress → pending_review → closed` 流转。

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

## 质量巡检（quality 模块）

「质量巡检」页（`/quality`）完全复刻安全分析的五 Agent 架构（QualityAgent → RagAgent → WorkOrderAgent → WorkerCareAgent → ReportAgent），语义改为建筑缺陷检测，质量工单由 `quality_inspector` 角色确认闭环。

- **5 类缺陷**：crack 裂缝（中危）/ leakage 渗漏（中危）/ abscission 剥落（高危）/ corrosion 锈蚀（中危）/ bulge 鼓包（高危）；
- **模型**：`backend/storage/models/yolov8n-5cls-mbdd.pt`，在 MBDD2025 数据集（14,471 张 UAV 墙体缺陷图，5 类）上微调 `yolov8n` 得到（imgsz=640、batch=48、RTX 5060 8GB 显存）。实际验收模型在第 40 epoch：验证集 mAP@50 = **0.8393**、mAP50-95 = **0.4492**、P = 0.8417、R = 0.7738。训练命令：
  ```powershell
  /d/anaconda3/envs/pytorch2.0/python.exe scripts/train_quality_yolo.py
  ```
  脚本自动按固定 seed 90/10 划分数据到 `data_demo/quality_yolo/`（不入 Git）、训练并把 `best.pt` 复制到模型路径，同时挑选 3 张单缺陷示例图到 `frontend/src/assets/samples/quality_*.jpg`。脚本内置 `torchvision.ops.nms` 的 **CPU NMS 回退补丁**（RTX 5060 Blackwell 无对应 CUDA NMS 内核，回退到 CPU 内核结果完全一致且快 ~18x），无需额外操作；`--reuse-train` 可跳过训练、直接发布现有 `best.pt`；
- **配置**（`backend/.env`）：
  ```env
  QUALITY_MODEL_PATH=storage/models/yolov8n-5cls-mbdd.pt
  QUALITY_CONF_THRESHOLD=0.45
  QUALITY_KNOWLEDGE_JSON_PATH=../data_demo/standards/quality_standards.json
  ```
  质量规范独立于安全规范（`data_demo/standards/quality_standards.json`，与 safety 一样只含项目内部有据条款，不编造标准编号）；RagAgent 按 `AgentRun.module` 检索对应知识库；
- **接口**：
  | 接口 | 说明 |
  | --- | --- |
  | `POST /api/v1/quality/analyze` | 上传巡检图片（Form：`image`/`project_id`/`location`/`work_type`/`description`/`demo_scenario`）→ 缺陷清单 + 五 Agent 轨迹 + 工单草稿 |
  | `GET /api/v1/quality/tasks` | 质量任务列表（可按 `project_id` 过滤） |
  | `GET /api/v1/quality/tasks/{task_id}` | 质量任务详情 |
  | `GET /api/v1/quality/status` | 模块状态 |
- **与 safety 的差异**：内部状态仍复用 `hazards`/`risk_level`，质量语义只体现在字段值上（`hazard_type`=缺陷码、`hazard_name`=缺陷中文名）；`AgentRun.module` 区分 `safety`/`quality`，两端任务与工单互不串扰；
- **降级规则**：质量模型缺失或加载失败时回退 `quality_mock` 并标记 `is_simulated=true`；模型就绪后 `provider_info.vision` 显示 `quality_hybrid:yolo`（可选叠加质量 LLM，配置方式同安全侧）；
- **相机拍照**：安全分析与质量巡检页面均支持本机摄像头直接拍照——`getUserMedia` 打开预览（复用实时监控页的设备选择模式），拍摄单帧转成 JPEG 图片后走同一个 analyze 闭环；画面仅在本浏览器内处理、不额外存储；无摄像头或权限被拒时仍可上传/使用示例图，不报错降级。

## 绿色建造 · 碳排核算（green 模块）

「绿色建造」页（`/green`）提供施工阶段碳排核算核心：按 GB/T 51366-2019《建筑碳排放计算标准》因子法 `排放 = 活动数据 × 排放因子`，把材料、运输、能耗三类活动数据折算为 A1-A3（建材生产）/ A4（建材运输）/ A5（施工过程）分阶段碳排放，并给出面积强度、主要贡献项、减排建议与报告预览。

- **因子库**：`data_demo/green/factors.json`，每条因子带 `code/name/unit/factor/factor_unit/source/year/verified/note`。`verified=true` 表示有公开权威来源可直接采用（如生态环境部《2022年度全国电网平均二氧化碳排放因子》0.5703 tCO2/MWh）；`verified=false` 为演示推算值（如 GB/T 51366-2019 附录 D/E 应用实例推算的 C30混凝土≈0.295 tCO2e/m³、热轧钢筋≈2.34 tCO2e/t），前端标「待核证」徽标、结果 `is_simulated=true`，正式核算需替换为经核证的因子数据；修改文件后重启后端生效；
- **配置**（`backend/.env`）：
  ```env
  GREEN_FACTORS_PATH=../data_demo/green/factors.json
  ```
- **接口**：
  | 接口 | 说明 |
  | --- | --- |
  | `POST /api/v1/green/analyze` | JSON 提交 `project_id/area_m2/scope/materials/transport/energy` → 分阶段排放 + 强度 + 建议 + 报告预览 |
  | `GET /api/v1/green/analyses` | 碳排核算历史（可按 `project_id` 过滤） |
  | `GET /api/v1/green/analyses/{id}` | 核算详情 |
  | `GET /api/v1/green/analyses/{id}/report` | 下载核算 Word 报告（`.docx`，python-docx 生成，缺失时降级为 `.txt`） |
  | `GET /api/v1/green/benchmark` | 同类项目碳排强度 z-score 对标（可按 `project_id` 高亮当前项目） |
  | `GET /api/v1/green/factors` | 排放因子库（含 verified 标记） |
- **与 safety/quality 的差异**：绿色为表单输入的计算核心，不走图像/五 Agent 闭环（绿色检测闭环规划中）；复用 `carbon_analyses` 表（`requested_by/area_m2/scope/is_simulated/report_preview/factor_version`），条目与分阶段明细存 `result_json`；未命中因子的条目按 0 计并给出警告，不中断请求；
- **降级规则**：因子库缺失或解析失败时返回空库并提示 `GREEN_FACTORS_PATH` 配置，所有条目按因子缺失处理。

## 统计分析（z-score）

全部使用纯 Python `statistics`，不引入 numpy/scipy/pandas；统计口径如下：

- **碳排强度对标**（`GET /green/benchmark`，绿色页「同类项目对标」卡）：对用户可见项目集合，每个项目取**最新一条有 `area_m2` 的核算**算强度 `total_emission/area_m2`；样本不足 2 个或标准差为 0 时显示降级文案而非报错。按强度升序排名，`z=(intensity-mean)/std` 为负表示优于均值，`better_than_pct` 为严格劣于当前项目的占比；
- **隐患/缺陷异常检测**（`GET /stats/anomalies`，仪表盘「异常波动检测」卡）：按天统计窗口内（默认 30 天，可切 safety/quality）的 Incident 数量，`z > z_threshold`（默认 2.5）的天标红为异常；空窗口或全零（标准差为 0）时降级显示。模块按 `metadata_json.module` 分拣，`safety` 兼容无 module 键的历史行；
- **风险评分 0-100**（安全/质量分析结果、工单草稿）：`rules/risk_rules.py::compute_risk_score` 用「隐患类型基准分 × 置信度缩放 + 重大缺陷加分」得到整数分（如 `no_helmet`≈87、`missing_guardrail`≈95）；视觉映射写入、读取接口兜底重算，历史数据也始终有分。

## 实时安全监测与硬件接口

「实时监控」页（`/safety/realtime`）把现场视频源逐帧送入后端 YOLO 检测，浏览器内叠加检测框，检测到高危违规时触发软报警；可选配 ESP32 硬报警（蜂鸣器）。

**视频源（浏览器内切换）**：

- **演示模式**：循环播放 `frontend/src/assets/samples/` 内置示例图，无摄像头也能演示检测与报警闭环；
- **本机摄像头**：`getUserMedia` 读取 USB 摄像头，画面仅在本浏览器内分析，不上传存储；
- **ESP32-CAM**：填写 `http://<ip>:81/stream` 的 MJPG 流地址，经后端代理接入。

**检测链路**：前端 canvas 按 1 帧/秒抓帧 → `POST /api/v1/safety/detect-frame` → YOLO 检测（不落库、不建工单、不跑 LLM）→ 返回 hazard 列表与归一化检测框 → 浏览器叠加画框。

**软报警规则**：连续 2 帧出现高危（高风险/重大风险）或未戴安全帽、未戴口罩、未穿反光背心违规即触发告警横幅、提示音与**语音播报**（浏览器 Web Speech 中文 TTS 念出隐患名，如"未佩戴安全帽"）；连续 3 帧正常自动解除。语音播报跟随「声音」开关，静音时仅保留视觉告警；浏览器不支持语音合成时自动跳过、不报错。抓帧被浏览器安全策略阻止（MJPG 跨域未授权）时自动降级为仅显示画面不检测。

**语音播报（浏览器 TTS）**：除实时监测外，**安全分析**与**质量巡检**页单张图片分析结果含高危/重大隐患时，也会用中文语音念出隐患/缺陷名（各页头部有"语音播报"开关，默认开启）。完全离线可用——Win11/Edge 自带中文语音，不依赖任何后端服务或新增依赖。

后端接口：

| 接口 | 说明 |
| --- | --- |
| `POST /api/v1/safety/detect-frame` | 实时单帧 YOLO 检测。模型缺失时返回 `available=false` 而非 500；临时帧写入 `backend/storage/tmp` 后立即清理 |
| `GET /api/v1/safety/mjpeg-proxy` | 透传 ESP32-CAM 的 MJPG 流并补 `Access-Control-Allow-Origin: *`（否则 canvas 抓帧会被浏览器阻止）。仅放行本机/内网地址（SSRF 防护）；token 走 query 参数，仅限本地演示场景 |

**ESP32 硬报警（可选，默认禁用）**：检测到 high/critical 隐患时，后端经 `BackgroundTasks` 后台 `POST` 到 `ALERT_WEBHOOK_URL`（fire-and-forget、失败静默、绝不阻塞检测主链路）。需在 ESP32 固件侧实现 HTTP 服务接收该 POST 并驱动 GPIO 蜂鸣器；固件不在本仓库。

```env
# backend/.env —— 未配置则硬报警禁用，不影响实时监测主链路
ALERT_WEBHOOK_URL=http://192.168.1.50/api/alert
```

## 工友助手（worker care）

「工友助手」页（`/worker-care`）把专业整改要求转成尊重、简短、可执行的现场提醒，回答由规范知识库 RAG 检索生成（内嵌《来源·条款》，高风险项提示暂停作业），未命中时回退本地模板，不替代安全员判断。

**语音输入（双通道）**：点击麦克风说话，优先使用浏览器 Web Speech（`SpeechRecognition`，zh-CN）本地识别，无需后端、无需配置；浏览器不支持时自动降级为 `MediaRecorder` 录音上传 `POST /api/v1/worker-care/transcribe` 转写。外设 USB 麦克风可在下拉中切换。

**后端转写是可插拔 ASR Provider**：未配置时接口返回 `available=false` + 中文 `reason`（不报错），前端因此走本地 Web Speech。要接 whisper 兼容服务：

```env
# backend/.env —— 复用上方 LLM_* 配置，POST {LLM_BASE_URL}/audio/transcriptions
SPEECH_PROVIDER=openai_compatible
```

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

### 规范问答（统一 RAG）

`POST /api/v1/knowledge/chat` 提供统一 RAG 回答组装：规范条文 → 相关风险提示 → 现场概况，逐段拼装并返回条款 citations；命中风险关键词时附加责任角色与时限（取自 `risk_rules`），传 `project_id` 时追加近 7 天现场概况。默认 `rag_only` 离线检索拼装，不调用任何外部模型；配置了 OpenAI-compatible 文本 Provider 后自动升级为 `rag_llm`（LLM 总结），调用失败或未配置一律静默降级回离线拼装，绝不伪造未授权条款。

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

页面和路由覆盖登录、注册、找回密码、仪表盘、项目管理、安全分析、实时监控、安全历史、整改工单、工单详情、工友助手、日报及历史、质量巡检、绿色碳排核算、知识库、个人资料、系统设置，以及 403/404 页面。

- `frontend/`：Vue 3 + TypeScript + Pinia + Vue Router；
- `backend/`：FastAPI + Pydantic + SQLAlchemy + Alembic + LangGraph；
- `data_demo/`：规范数据、演示图片、示例日报和材料数据；
- `scripts/`：本地启动、种子、知识导入、演示图片和 runbook 校验；
- `docs/`：产品、架构、API、数据库、算法、部署和演示文档。

## 能力边界

- 视觉识别可切换为 `safety_hybrid` 十类真实 YOLO 检测（未佩戴安全帽/未戴口罩/未穿安全背心/人/机械/车辆等）；模型未配置或加载失败时降级为模拟结果并显式标记 `is_simulated=true`；文本生成仍为本地模板 Provider；
- 实时监控为逐帧 YOLO 检测（1 帧/秒、仅本机分析），模型缺失时降级为仅显示画面不检测；ESP32 蜂鸣器硬报警为预留接口，需固件侧实现 HTTP 服务接收 webhook 驱动 GPIO；
- 安全分析与质量巡检页面支持本机摄像头拍照：拍摄单帧作为图片走 analyze 闭环（`getUserMedia` 仅在本浏览器内处理、不额外存储），仍为「定点拍、单图分析」，不做连续逐帧检测；
- `RETRIEVAL_PROVIDER=local_keyword` 是离线关键词能力，`chroma` 是本轮接入的真实持久化向量检索投影；
- 未命中本地规范时不编造条款，证据不足会提示人工补充；
- AI 只能生成工单草稿，人工确认后才写入正式工单；
- 日报核心数字来自 SQL 聚合，日报文案可由模板或真实文本 Provider 生成；
- 质量巡检已接入真实五 Agent 闭环：MBDD2025 训练的 YOLO 五类缺陷检测（模型缺失时降级 `quality_mock` 并标记 `is_simulated=true`），质量工单由质检员确认；
- 绿色建造已接入碳排核算核心：GB/T 51366-2019 因子法计算 A1-A3/A4/A5 分阶段排放（演示因子 `verified=false` 时 `is_simulated=true`），绿色五 Agent 检测闭环和真实碳排数据源仍为后续阶段；
- 工单列表展示负责人姓名（`assignee_name`），未指派时回退显示负责人 ID；
- 知识库提供统一 RAG 问答（`POST /knowledge/chat`），默认离线拼装、LLM 可选且失败自动降级；
- 工友助手回答由规范知识库 RAG 检索生成（内嵌《来源·条款》，未命中回退本地模板），语音输入优先浏览器 Web Speech（zh-CN）本地识别；未配置 ASR Provider 时后端 `/transcribe` 返回 `available=false` 而非报错；
- 统计分析（碳排强度 z-score 对标、隐患/缺陷异常波动检测、0-100 风险评分）全部为纯 `statistics` 计算，不依赖 numpy/scipy/pandas；
- 生产环境仍需更换 `SECRET_KEY`、使用 PostgreSQL/对象存储、限制 CORS、启用 HTTPS、集中日志和速率限制。

## 后续路线

- 接入语音提醒和权限审计；
- 为 `QualityAgent` 接入真实质量巡检数据源；
- 为 `GreenAgent` 接入真实材料和碳排数据源；
- 面向生产环境迁移 PostgreSQL、对象存储、HTTPS、集中日志和速率限制。
