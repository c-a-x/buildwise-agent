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
- `knowledge_documents`：规范本地知识库（安全 + 质量独立知识源）；
- `agent_runs` 的 `module` 列区分安全（`safety`）与质量（`quality`）任务，两者复用同一批表（`uploads`/`incidents`/`work_orders`）并互不串扰；
- `audit_logs`：审计扩展实体。绿色模块（`carbon_analyses`）仍为占位，尚未建表。

## 命令

```powershell
cd backend
python -m alembic upgrade head
python -m app.db.seed
```

当前首个迁移 `0001_initial` 由 ORM metadata 建立完整表结构，并保留 Alembic 版本控制入口。种子数据包含 4 个演示用户、1 个演示项目、20 条安全规范文档和 10 条质量规范文档。

`knowledge_documents` 的条款字段包括 `id`（稳定 document_id）、`source`、`title`、`article`、`category`、`content`、`version`、`effective_date` 和 `metadata_json`。`0003_knowledge_clause_metadata` 为已有 SQLite 数据库补充 `article` 与 `effective_date`；`metadata_json` 保存风险类型、关键词以及原始 `document_id` 等来源信息。

Chroma 是 SQLite 之外的持久化检索投影，默认目录为 `backend/storage/chroma`，collection 名称为 `buildwise-standards`。Docker 使用独立的 `buildwise-chroma` named volume，清空索引不会删除 SQLite 数据库。
