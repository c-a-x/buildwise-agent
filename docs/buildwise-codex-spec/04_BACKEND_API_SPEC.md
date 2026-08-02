# 04 后端与 API 设计文档

## 1. 技术栈

- Python 3.11 或更高兼容版本；
- FastAPI；
- Pydantic v2；
- SQLAlchemy 2；
- Alembic；
- JWT；
- 安全密码哈希库；
- LangGraph；
- pytest；
- httpx/TestClient；
- 可选：ChromaDB、Ultralytics、OpenAI 兼容客户端。

## 2. 分层职责

### API Endpoint

只负责：

- 读取 HTTP 参数；
- 鉴权和权限检查；
- 调用 Service；
- 返回 Schema。

### Service

负责：

- 事务；
- 业务流程；
- Workflow 调用；
- Repository 协调；
- 响应组装。

### Agent

负责单一节点的数据转换，不处理 HTTP，不创建全局数据库连接。

### Provider

封装外部能力，可替换：

- Vision；
- Retrieval；
- Text Generation。

### Repository

只负责数据库 CRUD 和查询。

## 3. 统一响应

```json
{
  "success": true,
  "message": "success",
  "data": {},
  "request_id": "REQ-20260802-ABC123"
}
```

错误：

```json
{
  "success": false,
  "message": "参数校验失败",
  "error": {
    "code": "VALIDATION_ERROR",
    "details": []
  },
  "request_id": "REQ-20260802-ABC123"
}
```

## 4. API 清单

### 4.1 系统

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/health` | 健康检查 |
| GET | `/api/v1/modules` | 模块实现状态 |

### 4.2 认证

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/auth/register` | 注册 |
| POST | `/api/v1/auth/login` | 登录 |
| GET | `/api/v1/auth/me` | 当前用户 |
| POST | `/api/v1/auth/logout` | 登出，MVP 可仅前端删除令牌 |
| POST | `/api/v1/auth/refresh` | 刷新令牌，可选 |

登录请求：

```json
{
  "username": "safety",
  "password": "BuildWise123!"
}
```

登录响应数据：

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "expires_in": 7200,
  "user": {
    "id": "USR-001",
    "username": "safety",
    "real_name": "演示安全员",
    "role": "safety_officer"
  }
}
```

### 4.3 项目

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/projects` | 当前用户可见项目 |
| POST | `/api/v1/projects` | 创建项目 |
| GET | `/api/v1/projects/{id}` | 项目详情 |

### 4.4 工作台

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/dashboard/summary?project_id=` | 指标和图表数据 |

### 4.5 安全分析

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/safety/analyze` | 运行安全闭环，返回工单草稿 |
| GET | `/api/v1/safety/tasks` | 历史列表 |
| GET | `/api/v1/safety/tasks/{task_id}` | 任务详情 |

`POST /safety/analyze` 使用 multipart：

- `image`；
- `project_id`；
- `location`；
- `work_type`；
- `description` 可选；
- `demo_scenario` 可选，仅 mock 模式使用。

响应数据必须包括：

```json
{
  "task_id": "TASK-...",
  "project_id": "PRJ-001",
  "upload_id": "UPL-...",
  "risk_level": "high",
  "hazards": [],
  "evidence": [],
  "work_order_draft": {},
  "worker_message": "",
  "report_preview": "",
  "agent_trace": [],
  "review_required": true,
  "is_simulated": true,
  "provider_info": {
    "vision": "mock",
    "retrieval": "local_keyword",
    "text": "template"
  }
}
```

### 4.6 工单

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/work-orders` | 确认草稿，创建正式工单 |
| GET | `/api/v1/work-orders` | 工单列表 |
| GET | `/api/v1/work-orders/{id}` | 工单详情 |
| PATCH | `/api/v1/work-orders/{id}/status` | 状态流转 |
| POST | `/api/v1/work-orders/{id}/attachments` | 整改附件，可选 |

创建工单必须携带来源任务：

```json
{
  "task_id": "TASK-001",
  "assignee_user_id": "USR-002",
  "deadline": "2026-08-03T18:00:00+08:00",
  "confirm_ai_draft": true
}
```

### 4.7 工友服务

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/worker-care/chat` | 文本问答 |
| POST | `/api/v1/worker-care/transcribe` | 语音占位或后续实现 |

### 4.8 报告

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/reports/daily/generate` | 生成/刷新日报 |
| GET | `/api/v1/reports/daily` | 按项目和日期查询 |
| GET | `/api/v1/reports` | 历史报告 |

### 4.9 知识库

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/knowledge/documents` | 内置规范列表 |
| GET | `/api/v1/knowledge/search?q=` | 关键词搜索 |
| POST | `/api/v1/knowledge/documents` | 文档上传，占位或管理员功能 |
| POST | `/api/v1/knowledge/reindex` | 重建索引，占位 |

### 4.10 扩展模块

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/quality/status` | 质量模块状态 |
| POST | `/api/v1/quality/analyze` | 未实现时返回 501 |
| GET | `/api/v1/green/status` | 绿色模块状态 |
| POST | `/api/v1/green/analyze` | 未实现时返回 501 |

## 5. 鉴权与权限

- JWT subject 保存用户 ID；
- 每次请求从数据库读取有效用户；
- `is_active=false` 禁止登录；
- 使用依赖函数实现角色限制；
- 项目数据必须验证用户是否属于该项目；
- 工友角色不可创建、分派或关闭工单；
- 质检员默认只读安全模块。

## 6. 文件上传

- 图片类型：JPEG、PNG、WEBP；
- 默认最大 10 MB；
- 使用随机 ID 文件名；
- 不信任原始文件名；
- 保存上传记录；
- 路径不得暴露本机绝对路径；
- API 通过受控静态地址返回文件；
- 删除临时文件需有明确策略。

## 7. 配置

`.env.example`：

```env
APP_NAME=BuildWise AI Agent
APP_ENV=development
DEBUG=true
API_PREFIX=/api/v1
SECRET_KEY=change-me
ACCESS_TOKEN_EXPIRE_MINUTES=120

DATABASE_URL=sqlite:///./storage/buildwise.db

UPLOAD_DIR=storage/uploads
ANNOTATED_DIR=storage/annotated
MAX_UPLOAD_MB=10

VISION_PROVIDER=mock
RETRIEVAL_PROVIDER=local_keyword
TEXT_PROVIDER=template

KNOWLEDGE_JSON_PATH=../data_demo/standards/safety_standards.json
CHROMA_DIR=storage/chroma

LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=

CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

## 8. 后端错误码

- `AUTH_INVALID_CREDENTIALS`
- `AUTH_TOKEN_EXPIRED`
- `AUTH_FORBIDDEN`
- `PROJECT_NOT_FOUND`
- `PROJECT_ACCESS_DENIED`
- `UPLOAD_INVALID_TYPE`
- `UPLOAD_TOO_LARGE`
- `SAFETY_ANALYSIS_FAILED`
- `WORK_ORDER_INVALID_TRANSITION`
- `KNOWLEDGE_NO_EVIDENCE`
- `MODULE_NOT_IMPLEMENTED`
- `INTERNAL_ERROR`

## 9. 后端启动

Codex 应提供：

```bash
cd backend
python -m venv .venv
# 激活虚拟环境
pip install -e ".[dev]"
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --port 8000
```
