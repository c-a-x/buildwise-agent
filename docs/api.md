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
| GET | `/api/v1/knowledge/search` | 规范知识检索 |
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

## 工单列表筛选

`GET /api/v1/work-orders` 支持 `project_id`、`status`、`risk_level`、`assignee_user_id`、`deadline_from` 和 `deadline_to` 查询参数。日期参数使用 ISO 8601 时间；详情响应会返回 `file_url`、`annotated_url` 和 `evidence`。
