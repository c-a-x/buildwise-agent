# 系统架构

BuildWise AI Agent 是一个默认离线可运行的 Vue 3 + FastAPI 应用，围绕“图片上传 → 五 Agent 分析 → 人工确认工单 → 状态流转 → 日报统计”构建最小安全闭环。

```text
Vue 3 / Pinia / Vue Router
          │ 统一 Axios envelope
          ▼
FastAPI API 层 ── Auth / Project / Safety / WorkOrder / Report
          │
          ▼
Service 层 ── Repository 层 ── SQLAlchemy ORM
          │
          ├── BuildWiseWorkflow
          │     ├── SafetyAgent     图片视觉检测
          │     ├── RagAgent         规范检索与证据
          │     ├── WorkOrderAgent   工单草稿
          │     ├── WorkerCareAgent  工人关怀消息
          │     └── ReportAgent      日报草稿/统计摘要
          │
          └── SQLite（默认）/ 可切换 PostgreSQL
```

## 关键边界

- Agent 只接收和返回工作流上下文，不处理 HTTP，也不直接创建数据库会话。
- API Endpoint 只做鉴权、参数校验和 Service 编排。
- 默认 Provider 为 MockVision、LocalKeywordRetriever、TemplateTextProvider，不需要外部 API Key。
- 任何模拟检测结果均带 `is_simulated=true`；工单必须经过人工确认才落库为正式工单。
- 日报中的数量、工单状态和风险趋势来自 SQL 聚合，不由模型编造。

## 运行形态

- 开发：后端 `8000`，前端 Vite `5173`。
- Docker：前端 `8080`，后端 `8000`，前端 Nginx 反向代理 `/api/` 和 `/storage/`。
- 数据：默认 `backend/storage/buildwise.db`，上传图片和生成报告也位于 `backend/storage/`。

