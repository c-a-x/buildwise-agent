# 05 数据库设计文档

## 1. 数据库策略

- 开发和比赛 Demo：SQLite；
- 正式部署：PostgreSQL；
- ORM：SQLAlchemy 2；
- 迁移：Alembic；
- 所有时间存储为带时区 UTC，响应时可由前端显示本地时间；
- 主键建议使用 UUID 字符串；
- 所有业务表包含 `created_at` 和 `updated_at`。

## 2. 枚举

### UserRole

- `admin`
- `project_manager`
- `safety_officer`
- `quality_inspector`
- `worker`

### RiskLevel

- `normal`
- `low`
- `medium`
- `high`
- `critical`

### WorkOrderStatus

- `pending`
- `in_progress`
- `pending_review`
- `closed`

### AgentRunStatus

- `pending`
- `running`
- `completed`
- `failed`
- `skipped`

## 3. 核心表

### 3.1 users

| 字段 | 类型 | 约束 |
|---|---|---|
| id | UUID/String | PK |
| username | String(32) | unique, index |
| password_hash | String | not null |
| real_name | String(64) | not null |
| role | Enum | not null |
| phone | String(32) | nullable |
| is_active | Boolean | default true |
| created_at | DateTime | not null |
| updated_at | DateTime | not null |

### 3.2 projects

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID/String | PK |
| code | String(32) | unique |
| name | String(128) | 项目名 |
| address | String(255) | 地址 |
| description | Text | 简介 |
| status | String(32) | active/archived |
| manager_user_id | FK users | 项目经理 |

### 3.3 project_members

联合唯一约束：`project_id + user_id`。

字段：

- id；
- project_id；
- user_id；
- project_role；
- joined_at。

### 3.4 uploads

- id；
- project_id；
- uploaded_by；
- original_name；
- stored_name；
- mime_type；
- size_bytes；
- relative_path；
- sha256；
- created_at。

### 3.5 agent_runs

记录一次安全工作流。

- id/task_id；
- project_id；
- upload_id；
- requested_by；
- location；
- work_type；
- description；
- risk_level；
- status；
- is_simulated；
- provider_info_json；
- trace_json；
- error_message；
- started_at；
- finished_at。

### 3.6 incidents

每个隐患一条。

- id；
- agent_run_id；
- project_id；
- upload_id；
- hazard_type；
- hazard_name；
- description；
- confidence；
- risk_level；
- bbox_json；
- review_required；
- reviewed_by；
- reviewed_at；
- created_at。

### 3.7 incident_evidences

- id；
- incident_id；
- source；
- article；
- content；
- score；
- metadata_json；
- created_at。

### 3.8 work_orders

- id；
- project_id；
- incident_id；
- source_task_id；
- title；
- problem_description；
- risk_level；
- location；
- assignee_user_id；
- created_by；
- deadline；
- status；
- rectification_requirements_json；
- review_requirements_json；
- worker_message；
- ai_generated；
- confirmed_by_human；
- closed_at；
- created_at；
- updated_at。

### 3.9 work_order_events

记录状态时间线：

- id；
- work_order_id；
- actor_user_id；
- event_type；
- from_status；
- to_status；
- note；
- attachment_upload_id；
- created_at。

### 3.10 daily_reports

唯一约束：`project_id + report_date`。

- id；
- project_id；
- report_date；
- statistics_json；
- content；
- generated_by；
- is_ai_generated；
- created_at；
- updated_at。

### 3.11 worker_messages

- id；
- project_id；
- user_id；
- question；
- answer；
- answer_source；
- is_simulated；
- created_at。

### 3.12 knowledge_documents

- id；
- title；
- source；
- version；
- category；
- file_path；
- status；
- created_by；
- created_at；
- updated_at。

MVP 使用 JSON 内置数据时也可以同步写入此表，或只保留接口和模型。

### 3.13 quality_inspections

占位表：

- id；
- project_id；
- upload_id；
- defect_type；
- severity；
- result_json；
- status；
- created_at。

### 3.14 carbon_analyses

占位表：

- id；
- project_id；
- source_upload_id；
- total_emission；
- result_json；
- created_at。

### 3.15 audit_logs

- id；
- user_id；
- action；
- resource_type；
- resource_id；
- detail_json；
- ip_address；
- created_at。

## 4. 关系

```text
users ──< project_members >── projects
projects ──< uploads
projects ──< agent_runs
agent_runs ──< incidents
incidents ──< incident_evidences
incidents ──0..1 work_orders
work_orders ──< work_order_events
projects ──< daily_reports
users ──< worker_messages
```

## 5. 索引

必须创建：

- users.username；
- projects.code；
- project_members(project_id, user_id)；
- agent_runs(project_id, created_at)；
- incidents(project_id, risk_level, created_at)；
- work_orders(project_id, status, deadline)；
- daily_reports(project_id, report_date)；
- audit_logs(user_id, created_at)。

## 6. 状态流转约束

允许：

```text
pending → in_progress
in_progress → pending_review
pending_review → in_progress
pending_review → closed
```

管理员或项目经理可以在有备注的情况下执行特殊回退；其他转换返回 `WORK_ORDER_INVALID_TRANSITION`。

## 7. 种子数据

Codex 必须生成：

- 4 个演示用户；
- 1 个演示项目；
- 4 个项目成员；
- 20 条左右规范条目；
- 可选 2 条历史隐患和工单；
- 密码均为 `BuildWise123!`，README 中明确仅用于本地演示。

## 8. 数据一致性

- 正式工单创建必须引用已有 `agent_run` 和 `incident`；
- 同一个隐患默认只允许一个活动工单；
- 日报统计必须从数据库查询，不从前端传入；
- 删除用户、项目和业务记录使用软删除或限制删除；
- 关闭工单时写 `closed_at` 和事件记录。
