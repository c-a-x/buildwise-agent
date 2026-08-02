# 数据库与迁移

默认数据库为 SQLite：`backend/storage/buildwise.db`。生产环境可通过 `BUILDWISE_DATABASE_URL` 切换到 PostgreSQL。

主要实体：

- `users`、`projects`、`project_members`：身份和项目权限；
- `uploads`：上传图片元数据、哈希、存储路径；
- `agent_runs`：一次图片分析及五 Agent trace；
- `incidents`、`incident_evidence`：风险事件与规范证据；
- `work_orders`、`work_order_events`：人工确认后的工单和状态历史；
- `daily_reports`：按项目和日期生成的日报；
- `worker_messages`：工人关怀消息；
- `knowledge_documents`：安全规范本地知识库；
- `quality_inspections`、`carbon_analyses`、`audit_logs`：质量、绿色和审计扩展实体。

## 命令

```powershell
cd backend
python -m alembic upgrade head
python -m app.db.seed
```

当前首个迁移 `0001_initial` 由 ORM metadata 建立完整表结构，并保留 Alembic 版本控制入口。种子数据包含 4 个演示用户、1 个演示项目和 20 条安全规范文档。

