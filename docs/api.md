# API 摘要

所有接口统一返回：

```json
{
  "success": true,
  "data": {},
  "error": null,
  "meta": {"request_id": "..."}
}
```

认证使用 Bearer Token。登录接口返回的 token 是本地开发 JWT。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/auth/login` | 登录 |
| POST | `/api/v1/auth/register` | 注册 |
| GET | `/api/v1/auth/me` | 当前用户 |
| GET | `/api/v1/projects` | 项目列表 |
| POST | `/api/v1/projects` | 创建项目 |
| GET | `/api/v1/dashboard/summary` | 首页统计 |
| POST | `/api/v1/safety/analyze` | 上传图片并运行五 Agent |
| GET | `/api/v1/safety/tasks` | 分析任务历史 |
| GET | `/api/v1/safety/tasks/{task_id}` | 分析详情 |
| POST | `/api/v1/work-orders` | 确认工单草稿 |
| GET | `/api/v1/work-orders` | 工单列表 |
| GET | `/api/v1/work-orders/{id}` | 工单详情 |
| PATCH | `/api/v1/work-orders/{id}/status` | 状态流转；关闭必须提供复查备注 |
| POST | `/api/v1/work-orders/{id}/attachments` | 保存整改图片并关联工单事件 |
| POST | `/api/v1/reports/daily/generate` | 生成日报 |
| GET | `/api/v1/reports/daily` | 日报历史 |
| POST | `/api/v1/worker-care/messages` | 工人关怀消息 |
| GET | `/api/v1/knowledge/documents` | 已导入规范文档/条款 |
| GET | `/api/v1/knowledge/search` | 规范知识检索 |
| GET | `/api/v1/knowledge/index/status` | Provider、索引状态、文档数和条款数 |
| POST | `/api/v1/knowledge/reindex` | 按当前知识源重建 Chroma 索引 |
| GET | `/api/v1/quality/status` | 质量模块占位状态 |
| GET | `/api/v1/green/status` | 绿色模块占位状态 |
| GET | `/api/v1/health` | 健康检查，包含 Provider 与 SQLite 连接状态 |

健康检查的 `data.database` 会由后端执行真实 `SELECT 1` 得出：

```json
{
  "status": "connected",
  "dialect": "sqlite",
  "persistent": true
}
```

## 图片分析

`POST /api/v1/safety/analyze` 使用 `multipart/form-data`，字段包括：

- `project_id`：项目 ID；
- `location`：位置；
- `work_type`：作业类型；
- `description`：现场描述，可选；
- `image`：jpg/png/webp 图片；
- `demo_scenario`：可选的离线演示场景，如 `no_helmet`、`missing_guardrail`、`no_safety_vest`、`normal`。

返回值包含 `risk_level`、`hazards`、`evidence`、`work_order_draft`、`worker_message`、`agent_trace` 和 `is_simulated`。

## 规范知识检索

`GET /api/v1/knowledge/search?q=安全帽` 的每条命中包含 `source`、`article`、`content`、`score` 和 `metadata`，并保留 `document_id`、标题、分类、版本和生效日期。没有充分依据时 `data` 为 `[]`。

`GET /api/v1/knowledge/index/status` 返回当前 `provider`（`local_keyword` 或 `chroma`）、`indexed`、`document_count`、`clause_count` 和 Chroma collection 信息。`POST /api/v1/knowledge/reindex` 在 Chroma 模式下读取 `KNOWLEDGE_JSON_PATH` 并重建持久化投影；关键词模式保持 JSON 直读，不需要向量重建。

## 工单列表筛选

`GET /api/v1/work-orders` 支持 `project_id`、`status`、`risk_level`、`assignee_user_id`、`deadline_from` 和 `deadline_to` 查询参数。日期参数使用 ISO 8601 时间；详情响应会返回 `file_url`、`annotated_url` 和 `evidence`。
