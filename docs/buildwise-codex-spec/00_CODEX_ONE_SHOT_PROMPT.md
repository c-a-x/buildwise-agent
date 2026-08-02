# 00 Codex 一键执行指令

你现在位于“筑智共生 AI Agent”项目根目录。根目录已经存在 `frontend/` Vue 工程和 `backend/` FastAPI 工程。

请严格阅读并执行本目录中的：

1. `AGENTS.md`
2. `01_PRODUCT_REQUIREMENTS.md`
3. `02_ARCHITECTURE_DIRECTORY.md`
4. `03_FRONTEND_SPEC.md`
5. `04_BACKEND_API_SPEC.md`
6. `05_DATABASE_DESIGN.md`
7. `06_AGENT_ALGORITHM_DESIGN.md`
8. `07_TEST_ACCEPTANCE.md`
9. `08_DEPLOYMENT_AND_RUNBOOK.md`

## 执行要求

- 先检查现有前后端结构和依赖，不要无条件删除或覆盖已有代码；
- 在现有工程基础上补齐文件；
- 先实现完整页面和路由骨架；
- 再实现注册登录、数据库、核心 Agent 闭环；
- 默认使用离线可运行的 `mock + local_keyword + template` Provider；
- 模拟结果必须显式显示 `is_simulated=true`；
- 所有 AI 结论必须 `review_required=true`；
- Agent 只生成工单草稿，用户确认后才创建正式工单；
- 质量巡检和绿色建造先做完整占位页面及状态接口；
- 不依赖任何付费 API 才能启动；
- 不将密钥或绝对路径写入源码；
- 所有数据库变更通过 Alembic；
- 后端运行 pytest；
- 前端运行 TypeScript 检查和生产构建；
- 发现错误后直接修复并重新运行验证；
- 不要在完成前停下来只给建议；
- 不要只输出代码片段，必须实际创建和修改文件；
- 最后更新 README，并输出：
  1. 已创建/修改文件；
  2. 启动命令；
  3. 测试结果；
  4. 当前使用的 Provider；
  5. 尚未实现的真实模型能力。

## 实施顺序

### Phase 1：基础工程

- 配置、日志、统一响应、异常处理；
- 完整 Vue 路由、布局、菜单和占位页面；
- 后端完整路由骨架；
- 数据库和迁移。

### Phase 2：用户与项目

- 注册登录；
- JWT；
- 角色权限；
- 演示项目和演示账号。

### Phase 3：核心闭环

- 图片上传；
- LangGraph 状态和节点；
- SafetyAgent；
- RagAgent；
- WorkOrderAgent；
- WorkerCareAgent；
- ReportAgent；
- 工单确认和状态流转；
- 日报统计。

### Phase 4：前端联调

- 工作台；
- 安全分析；
- 工单列表/详情；
- 日报；
- 工友助手；
- 知识库；
- 占位模块。

### Phase 5：验证与交付

- pytest；
- 前端 build；
- 端到端手动验证；
- Docker 和脚本；
- README。

现在开始执行。
