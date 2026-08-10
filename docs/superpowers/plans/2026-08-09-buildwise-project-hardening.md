# BuildWise 项目全链路收敛实施计划
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 收敛当前仓库中所有可复现、属于项目自身的问题，建立从数据库迁移、后端 API、离线 Agent 闭环到前端页面和启动/验收脚本的可重复交付链路。外部模型权重、外部 LLM、天气、ASR、TTS 和硬件广播不在仓库内，因此只实现真实能力的可检测状态、明确降级和配置说明，不把模拟结果伪装成真实推理。

**Architecture:** 保持现有 Vue 3 + TypeScript / FastAPI + SQLAlchemy / Alembic 分层。后端继续由 Pydantic Schema、Service 和 Repository 负责业务，Endpoint 只做鉴权、依赖注入和 envelope 返回；前端通过 API 模块和 Pinia Store 连接现有页面。所有修复先有失败测试或失败验收命令，再由独立子代理实现，并在每个任务后进行规范审查和代码质量审查。

**Tech Stack:** Python 3.12、FastAPI、SQLAlchemy、Alembic、pytest、SQLite（默认离线演示）、Vue 3、TypeScript、Pinia、Axios、Vitest、Vite、PowerShell。

---

## 验收基线与边界

- [x] `backend/venv/Scripts/python.exe -m pytest -q` 通过。
- [x] `backend/venv/Scripts/python.exe -m alembic check` 通过，且从空 SQLite 数据库执行 `upgrade head` 后与 SQLAlchemy metadata 一致。
- [x] `scripts/test_runbooks.ps1`、`scripts/e2e_demo.py` 在仓库根目录执行通过；E2E 覆盖安全、质量、绿色、工单人工确认、日报 SQL 统计和知识检索。
- [x] `frontend/npm.cmd run test:unit -- --run`、`frontend/npm.cmd run type-check`、`frontend/npm.cmd run build` 通过。
- [x] 项目管理与用户中心不再把已有 API 能力显示为禁用；表单错误、权限和保存成功状态可见。
- [x] 系统状态页明确区分 `available`、`configured`、`simulated`、`not_configured`、`unavailable` 和数据库状态；默认离线启动仍无需外部 API Key。
- [x] 新增一个根目录可执行的全量验证脚本，输出每个阶段的失败原因，并在文档中给出启动、演示账号及模拟/真实能力边界。
- [x] 不承诺当前机器已经运行真实 YOLO/Ultralytics、Chroma 索引、外部 LLM、天气、ASR、TTS 或硬件广播；这些能力必须通过配置、依赖和资源预检后才标记为可用。

## 实施任务

### Task 1: 修复 Alembic schema drift 并让 runbook 可重复

**Files:**
- Create `backend/alembic/versions/0009_schema_alignment.py`
- Create `backend/tests/test_schema_alignment.py`
- Modify `scripts/test_runbooks.ps1`
- Modify `README.md` or `docs/runbook.md` only where the verified command path is documented

**Steps:**

- [x] 先添加回归测试：验证现有数据库运行 `alembic check` 失败的两个差异（`agent_runs.module` 索引和 `carbon_analyses.requested_by` 外键），并验证空数据库完整升级后 metadata 对齐。
- [x] 新增 0009 migration：幂等创建 `ix_agent_runs_module`，并以兼容 SQLite 的方式为 `carbon_analyses.requested_by` 补充 `users.id` 外键；迁移必须能处理已经存在的演示数据库，不删除业务数据。
- [x] 将 `scripts/test_runbooks.ps1` 的迁移、seed、health、schema check 顺序固定下来，确保从仓库根目录执行不依赖当前 shell 目录。
- [x] 运行单测、`alembic upgrade head`、`alembic check` 和 runbook；确认数据库版本为 0009 且现有数据仍可查询。

### Task 2: 修复官方 API E2E 合约并覆盖四个业务模块

**Files:**
- Modify `scripts/e2e_demo.py`
- Create or modify `backend/tests/test_e2e_demo_contract.py`
- Modify `README.md` or `docs/api.md` only for the verified E2E command and sample paths

**Steps:**

- [x] 先增加失败合约测试，锁定当前 E2E 的两个回归：质量样例应使用 `frontend/src/assets/samples/quality_1_crack.jpg`，质量/绿色模块当前状态应为 `available` 而不是 `planned`。
- [x] 修正演示脚本，并实际调用质量分析和绿色核算；断言五 Agent trace、`is_simulated`、质量缺陷/证据、绿色排放结果和因子警告。
- [x] 保留并强化安全分析、工单二次确认幂等、状态闭环、日报生成、知识检索的断言；日报数字必须来自响应中的 SQL 统计字段。
- [x] 在独立测试数据库和当前 SQLite 演示数据库上分别执行合约测试与脚本，避免只验证静态文本。

### Task 3: 解锁项目管理页面的创建闭环

**Files:**
- Modify `frontend/src/api/projects.ts`
- Modify `frontend/src/stores/project.ts`
- Modify `frontend/src/views/projects/ProjectListView.vue`
- Add focused tests under `frontend/src/views/projects/__tests__/`
- Modify `frontend/src/assets/main.css` only for the new modal/form states if required

**Steps:**

- [x] 先写 Vitest 失败测试：管理员/项目经理可以打开创建表单并提交，普通角色不显示创建入口，API 错误显示在表单内。
- [x] 接入已有 `POST /api/v1/projects`，补充强类型的创建 payload、loading/error 状态、字段校验和成功后刷新/选中项目。
- [x] 以当前统一视觉风格实现非阻塞的表单弹层或面板；下拉框、滚动区域、焦点态、键盘关闭和移动端宽度必须与项目现有 token 一致。
- [x] 运行前端单测、type-check 和 build，确认没有 `any` 和未使用导入。

### Task 4: 补齐用户资料编辑和密码变更的安全闭环

**Files:**
- Modify `backend/app/schemas/auth.py`
- Modify `backend/app/services/auth_service.py`
- Modify `backend/app/api/v1/endpoints/users.py`
- Modify `backend/tests/test_auth.py`
- Modify `frontend/src/types/auth.ts`
- Modify `frontend/src/api/auth.ts`
- Modify `frontend/src/stores/auth.ts`
- Modify `frontend/src/views/user/UserProfileView.vue`
- Add focused tests under `frontend/src/views/user/__tests__/`

**Steps:**

- [x] 先写后端失败测试：认证用户只能更新自己的 `real_name`/`phone`，密码变更必须校验旧密码、新密码长度和二次确认，并记录审计日志；不能修改用户名、角色或激活状态。
- [x] 在 `/api/v1/users/me` 增加 PATCH Schema/Service 闭环，新增安全的密码变更 endpoint，保持统一 envelope 和权限边界。
- [x] 将用户中心从“只读/后续版本”改为可编辑资料与修改密码两个明确操作；提交期间禁用按钮、错误可读、成功后刷新 auth store。
- [x] 将找回密码页改成准确的离线恢复说明：提供已登录用户修改密码入口和管理员协助路径，不显示虚假的“规划中已接入”能力。
- [x] 运行后端 auth/audit 测试和前端组件测试，验证敏感字段不会回显或写入日志。

### Task 5: 把 Provider、模块和数据库运行状态变成可验证的产品信息

**Files:**
- Modify `backend/app/services/runtime_service.py`
- Modify `backend/app/api/v1/endpoints/health.py`
- Modify `backend/tests/test_health.py` and/or create `backend/tests/test_runtime_capabilities.py`
- Modify `frontend/src/api/system.ts`
- Modify `frontend/src/views/system/SystemSettingsView.vue`
- Add focused tests under `frontend/src/views/system/__tests__/`
- Create `scripts/check_providers.py`
- Create `backend/tests/test_check_providers.py` if the script logic is imported for testing

**Steps:**

- [x] 先写失败测试，覆盖默认 mock/local/template、缺少 YOLO 权重或 `ultralytics`、空 Chroma 索引、未配置 LLM/天气/语音时的明确状态和原因。
- [x] 后端 health 增加只读 capability 详情，复用现有配置和 Provider 发现逻辑，不在 health 请求中执行昂贵推理或外部网络调用。
- [x] 新增离线可执行的 Provider 预检脚本，输出配置、依赖、资源、预计降级路径；缺少可选真实资源时用可读的 warning/skip，不让默认开发环境失败。
- [x] 系统设置页展示能力卡片、真实/模拟标签、数据库持久化状态和下一步配置项；删除没有行动含义的禁用占位文案。
- [x] 保持所有模拟结果 `is_simulated=true`，运行测试验证 provider status 与接口返回一致。

### Task 6: 建立全量验证命令并完成文档交付

**Files:**
- Create `scripts/verify_all.ps1`
- Modify `README.md`
- Modify `docs/api.md` if endpoint/schema changes require it
- Modify `scripts/dev.ps1` only if verification finds a regression; preserve the existing port reuse and health-wait fix

**Steps:**

- [x] 先定义脚本失败策略：依次执行后端测试、migration check、runbook、E2E、前端单测、type-check、build、`git diff --check`，每阶段带清晰标题并保留原始失败码。
- [x] 为脚本增加最小 PowerShell 级别验证或文档化的逐项命令，确保从仓库根目录、PowerShell 新会话和已有 8000 端口场景都能复现。
- [x] 更新启动说明：`powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dev.ps1`；列出演示账号（manager/safety/quality/worker/admin，如 seed 实际提供）；列出默认模拟与可选真实 Provider 边界。
- [x] 执行完整验收矩阵并记录输出；任何一项失败都回到对应任务修复，不以“单测通过”替代数据库或 HTTP 验收。

## 最终交付门槛

- [x] 所有 Task 1–6 的 checkbox 完成。
- [x] 后端 pytest、Alembic check、runbook、E2E 全部通过。
- [x] 前端 unit、type-check、build 全部通过。
- [x] Provider 预检输出与 README 的能力边界一致。
- [x] 通过最终代码质量审查；只报告实际完成的能力，不把外部资源缺失描述成已修复。
