# 筑智共生 AI Agent 完整项目规格书
## 供 Codex 一键生成 Vue + FastAPI + Database + Agent Workflow

> 本文是项目唯一的总规格。若分拆文档与本文冲突，以本文为准。

# 01 产品需求与范围

## 1. 项目名称

- 中文名：筑智共生 AI Agent
- 英文名：BuildWise AI Agent
- 产品形态：面向建筑施工项目的企业级 Web 管理平台
- 核心价值：把 AI 从“回答问题”推进到“识别问题—检索依据—生成任务—通知人员—汇总管理”的业务闭环。

## 2. 核心业务闭环

```text
用户登录
  → 选择项目
  → 上传施工现场图片
  → SafetyAgent 识别安全隐患
  → RagAgent 检索规范或企业制度
  → WorkOrderAgent 生成整改工单草稿
  → 人工确认并落库
  → WorkerCareAgent 生成工友提醒
  → ReportAgent 汇总当日隐患与工单
  → 工作台展示统计和日报
```

## 3. 开发原则

采用“完整产品外壳 + 一条真实可运行纵向链路 + 其他模块占位”的策略。

### 3.1 第一阶段必须真实可用

- 用户注册、登录、退出和当前用户查询；
- 项目列表和默认演示项目；
- 施工图片上传及文件保存；
- 五节点 Agent 工作流；
- 规范依据检索；
- 整改工单持久化；
- 工单四状态流转；
- 工友提醒生成；
- 当日日报统计；
- 工作台统计；
- 前后端联调；
- 自动化测试；
- 无第三方模型密钥也能启动。

### 3.2 第一阶段必须存在但允许占位

- 安全历史记录；
- 工友语音输入；
- 工程质量巡检；
- 绿色低碳分析；
- 规范文档上传和向量重建；
- 系统设置；
- 用户中心的高级设置；
- 管理员后台。

占位模块必须有正式页面、路由、导航和模块状态接口，不得出现空白页或不存在的路由。

## 4. 用户角色

| 角色 | 枚举值 | 主要权限 |
|---|---|---|
| 系统管理员 | `admin` | 用户、项目、知识库和全部业务数据 |
| 项目经理 | `project_manager` | 查看项目全局数据、分派工单、关闭工单、生成日报 |
| 安全员 | `safety_officer` | 安全分析、创建工单、提交复查、查看规范 |
| 质检员 | `quality_inspector` | 质量巡检页面、查看项目数据、查看安全结果 |
| 工友 | `worker` | 工友助手、本人提醒、有限项目安全信息 |

MVP 注册页允许选择非管理员角色。管理员只能通过种子数据或后台创建。

## 5. 页面清单

### 5.1 公共页面

- `/login` 登录；
- `/register` 注册；
- `/forgot-password` 找回密码占位；
- `/403` 无权限；
- `/:pathMatch(.*)*` 404。

### 5.2 登录后页面

- `/dashboard` 项目工作台；
- `/projects` 项目列表；
- `/safety/analyze` 现场安全分析；
- `/safety/history` 安全分析历史；
- `/work-orders` 整改工单列表；
- `/work-orders/:id` 工单详情；
- `/worker-care` 工友助手；
- `/reports/daily` 项目日报；
- `/reports/history` 历史报告；
- `/quality` 质量巡检占位；
- `/green` 绿色建造占位；
- `/knowledge` 规范知识库；
- `/profile` 用户中心；
- `/settings` 系统设置占位。

## 6. 核心用户故事

### US-01 注册登录

用户可以注册账号，选择角色，登录后获得访问令牌。页面刷新后登录状态可恢复，令牌失效时自动回到登录页。

### US-02 安全分析

安全员上传现场图片，填写项目、位置和作业类型，系统运行 Agent 工作流，显示隐患、风险等级、规范依据、整改工单草稿、工友提醒和执行轨迹。

### US-03 工单确认

Agent 产生的结果必须标记为 AI 草稿。安全员点击确认后创建正式工单。正式工单可以按“待整改、整改中、待复查、已关闭”流转。

### US-04 日报

项目经理选择日期，系统根据数据库中的真实隐患和工单统计生成日报。所有数字由 SQL 统计产生，不允许由大模型计算。

### US-05 占位模块

用户进入质量巡检或绿色建造页面时，看到模块介绍、计划能力、当前状态和预计接入的数据类型，而不是空白页。

## 7. 非功能要求

- 所有 API 返回统一响应格式；
- 重要操作写审计日志；
- 密码只保存哈希；
- 上传文件限制类型和大小；
- 后端统一异常处理；
- 前端有加载、空状态和错误提示；
- AI 输出必须携带 `review_required` 和 `is_simulated`；
- 默认使用 SQLite，允许切换 PostgreSQL；
- 默认使用本地模拟/规则提供者，无需 API Key；
- Windows、macOS、Linux 均可启动；
- 后端必须通过 pytest；
- 前端必须通过 TypeScript 检查和生产构建。


---

# 02 系统架构与完整目录

## 1. 总体架构

```text
Vue 3 + TypeScript
        │
        │ REST / JSON / multipart
        ▼
FastAPI API 层
        │
        ▼
Service 业务层
        │
        ├── Auth / Project / Dashboard
        └── SafetyWorkflowService
                    │
                    ▼
               LangGraph
        ┌──────────┼──────────┐
        ▼          ▼          ▼
   Vision      Retrieval     Text
   Provider    Provider      Provider
        │          │          │
        ▼          ▼          ▼
      文件       规范库      模板/LLM
                    │
                    ▼
         SQLAlchemy Repository
                    │
             SQLite / PostgreSQL
```

## 2. 依赖方向

必须遵守：

```text
Vue View
  → frontend/src/api
  → FastAPI Endpoint
  → Service
  → Workflow / Repository
  → Agent
  → Provider（Vision / RAG / LLM）
  → Database / File Storage
```

禁止：

- Vue 直接调用模型；
- API Endpoint 中直接写 YOLO 或 SQL；
- Agent 直接处理 HTTP 请求；
- Agent 直接拼接数据库连接；
- 前端自行推断风险等级；
- 不同 Agent 返回不一致的字段；
- 把密钥写入源码。

## 3. 完整项目目录

Codex 必须保留现有 `frontend/` 和 `backend/` 工程，在其基础上补齐以下结构。若已有同名文件，先阅读并合并，不得无条件覆盖。

```text
buildwise-agent/
├── AGENTS.md
├── README.md
├── .gitignore
├── .editorconfig
├── docker-compose.yml
├── Makefile
├── scripts/
│   ├── dev.ps1
│   ├── dev.sh
│   ├── seed_demo.py
│   └── ingest_knowledge.py
├── data_demo/
│   ├── images/
│   │   ├── safety_no_helmet.jpg
│   │   └── safety_normal.jpg
│   ├── standards/
│   │   └── safety_standards.json
│   ├── audio/
│   │   └── README.md
│   ├── reports/
│   │   └── daily_report_sample.json
│   └── materials/
│       └── material_sample.csv
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── database.md
│   ├── algorithms.md
│   └── demo-script.md
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── api/
│   │   │   ├── http.ts
│   │   │   ├── auth.ts
│   │   │   ├── projects.ts
│   │   │   ├── dashboard.ts
│   │   │   ├── safety.ts
│   │   │   ├── workOrders.ts
│   │   │   ├── workerCare.ts
│   │   │   ├── reports.ts
│   │   │   ├── knowledge.ts
│   │   │   └── modules.ts
│   │   ├── assets/
│   │   │   ├── styles/
│   │   │   │   ├── variables.css
│   │   │   │   ├── reset.css
│   │   │   │   └── global.css
│   │   │   └── images/
│   │   ├── components/
│   │   │   ├── common/
│   │   │   │   ├── AppPageHeader.vue
│   │   │   │   ├── AppEmpty.vue
│   │   │   │   ├── AppLoading.vue
│   │   │   │   ├── AppError.vue
│   │   │   │   └── ModulePlaceholder.vue
│   │   │   ├── layout/
│   │   │   │   ├── AppSidebar.vue
│   │   │   │   ├── AppTopbar.vue
│   │   │   │   └── UserMenu.vue
│   │   │   ├── dashboard/
│   │   │   │   ├── MetricCard.vue
│   │   │   │   ├── RiskTrendChart.vue
│   │   │   │   └── WorkOrderStatusChart.vue
│   │   │   ├── safety/
│   │   │   │   ├── SafetyUploadForm.vue
│   │   │   │   ├── DetectionPreview.vue
│   │   │   │   ├── HazardList.vue
│   │   │   │   ├── EvidenceList.vue
│   │   │   │   └── AgentTrace.vue
│   │   │   ├── work-order/
│   │   │   │   ├── WorkOrderCard.vue
│   │   │   │   ├── WorkOrderStatusTag.vue
│   │   │   │   └── WorkOrderTimeline.vue
│   │   │   └── report/
│   │   │       ├── DailyReportPreview.vue
│   │   │       └── ReportMetrics.vue
│   │   ├── layouts/
│   │   │   ├── AuthLayout.vue
│   │   │   └── MainLayout.vue
│   │   ├── router/
│   │   │   ├── index.ts
│   │   │   └── guards.ts
│   │   ├── stores/
│   │   │   ├── auth.ts
│   │   │   ├── project.ts
│   │   │   ├── safety.ts
│   │   │   └── app.ts
│   │   ├── types/
│   │   │   ├── api.ts
│   │   │   ├── auth.ts
│   │   │   ├── project.ts
│   │   │   ├── safety.ts
│   │   │   ├── workOrder.ts
│   │   │   ├── report.ts
│   │   │   └── module.ts
│   │   ├── utils/
│   │   │   ├── storage.ts
│   │   │   ├── date.ts
│   │   │   ├── risk.ts
│   │   │   └── validation.ts
│   │   ├── views/
│   │   │   ├── auth/
│   │   │   │   ├── LoginView.vue
│   │   │   │   ├── RegisterView.vue
│   │   │   │   └── ForgotPasswordView.vue
│   │   │   ├── dashboard/DashboardView.vue
│   │   │   ├── projects/ProjectListView.vue
│   │   │   ├── safety/
│   │   │   │   ├── SafetyAnalysisView.vue
│   │   │   │   └── SafetyHistoryView.vue
│   │   │   ├── work-orders/
│   │   │   │   ├── WorkOrderListView.vue
│   │   │   │   └── WorkOrderDetailView.vue
│   │   │   ├── worker-care/WorkerCareView.vue
│   │   │   ├── reports/
│   │   │   │   ├── DailyReportView.vue
│   │   │   │   └── ReportHistoryView.vue
│   │   │   ├── quality/QualityInspectionView.vue
│   │   │   ├── green/GreenConstructionView.vue
│   │   │   ├── knowledge/KnowledgeBaseView.vue
│   │   │   ├── user/UserProfileView.vue
│   │   │   ├── system/SystemSettingsView.vue
│   │   │   └── error/
│   │   │       ├── ForbiddenView.vue
│   │   │       └── NotFoundView.vue
│   │   ├── App.vue
│   │   └── main.ts
│   ├── .env.example
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
└── backend/
    ├── app/
    │   ├── api/
    │   │   ├── dependencies.py
    │   │   └── v1/
    │   │       ├── router.py
    │   │       └── endpoints/
    │   │           ├── auth.py
    │   │           ├── users.py
    │   │           ├── projects.py
    │   │           ├── dashboard.py
    │   │           ├── safety.py
    │   │           ├── work_orders.py
    │   │           ├── worker_care.py
    │   │           ├── reports.py
    │   │           ├── knowledge.py
    │   │           ├── quality.py
    │   │           ├── green.py
    │   │           └── health.py
    │   ├── agents/
    │   │   ├── safety_agent.py
    │   │   ├── rag_agent.py
    │   │   ├── work_order_agent.py
    │   │   ├── worker_care_agent.py
    │   │   └── report_agent.py
    │   ├── workflow/
    │   │   ├── state.py
    │   │   ├── routing.py
    │   │   └── graph.py
    │   ├── providers/
    │   │   ├── vision/
    │   │   │   ├── base.py
    │   │   │   ├── mock.py
    │   │   │   └── ultralytics.py
    │   │   ├── retrieval/
    │   │   │   ├── base.py
    │   │   │   ├── local_keyword.py
    │   │   │   └── chroma.py
    │   │   └── text/
    │   │       ├── base.py
    │   │       ├── template.py
    │   │       └── openai_compatible.py
    │   ├── rules/
    │   │   ├── risk_rules.py
    │   │   ├── assignment_rules.py
    │   │   └── deadline_rules.py
    │   ├── schemas/
    │   │   ├── common.py
    │   │   ├── auth.py
    │   │   ├── user.py
    │   │   ├── project.py
    │   │   ├── safety.py
    │   │   ├── work_order.py
    │   │   ├── report.py
    │   │   ├── knowledge.py
    │   │   └── module.py
    │   ├── services/
    │   │   ├── auth_service.py
    │   │   ├── project_service.py
    │   │   ├── dashboard_service.py
    │   │   ├── safety_service.py
    │   │   ├── work_order_service.py
    │   │   ├── worker_care_service.py
    │   │   ├── report_service.py
    │   │   └── knowledge_service.py
    │   ├── models/
    │   │   ├── user.py
    │   │   ├── project.py
    │   │   ├── project_member.py
    │   │   ├── upload.py
    │   │   ├── incident.py
    │   │   ├── incident_evidence.py
    │   │   ├── work_order.py
    │   │   ├── work_order_event.py
    │   │   ├── daily_report.py
    │   │   ├── agent_run.py
    │   │   ├── worker_message.py
    │   │   ├── knowledge_document.py
    │   │   ├── quality_inspection.py
    │   │   ├── carbon_analysis.py
    │   │   └── audit_log.py
    │   ├── repositories/
    │   │   ├── user_repository.py
    │   │   ├── project_repository.py
    │   │   ├── incident_repository.py
    │   │   ├── work_order_repository.py
    │   │   ├── report_repository.py
    │   │   └── knowledge_repository.py
    │   ├── db/
    │   │   ├── base.py
    │   │   ├── session.py
    │   │   ├── init_db.py
    │   │   └── seed.py
    │   ├── core/
    │   │   ├── config.py
    │   │   ├── security.py
    │   │   ├── exceptions.py
    │   │   └── logging.py
    │   ├── prompts/
    │   │   ├── work_order.py
    │   │   ├── worker_care.py
    │   │   └── report.py
    │   ├── utils/
    │   │   ├── files.py
    │   │   ├── ids.py
    │   │   ├── dates.py
    │   │   └── images.py
    │   └── main.py
    ├── alembic/
    ├── storage/
    │   ├── uploads/.gitkeep
    │   ├── annotated/.gitkeep
    │   ├── reports/.gitkeep
    │   └── chroma/.gitkeep
    ├── tests/
    │   ├── conftest.py
    │   ├── test_auth.py
    │   ├── test_health.py
    │   ├── test_safety_workflow.py
    │   ├── test_work_orders.py
    │   ├── test_reports.py
    │   └── test_permissions.py
    ├── .env.example
    ├── alembic.ini
    ├── pyproject.toml
    └── run.py
```

## 4. 默认运行模式

默认配置必须完全离线可运行：

```env
VISION_PROVIDER=mock
RETRIEVAL_PROVIDER=local_keyword
TEXT_PROVIDER=template
DATABASE_URL=sqlite:///./storage/buildwise.db
```

真实模型为可选适配器，不得成为首次启动的前置条件。


---

# 03 前端设计文档

## 1. 技术栈

- Vue 3；
- TypeScript；
- Vite；
- Vue Router；
- Pinia；
- Axios；
- Element Plus；
- ECharts；
- CSS Variables。

若现有工程已经选择其他等价 UI 库，Codex 可以沿用，但必须保持统一，禁止混用多套大型 UI 框架。

## 2. 视觉方向

- 企业级建筑施工管理后台；
- 深色导航 + 浅色内容区，或全局深色科技主题；
- 蓝色、青色作为主强调色；
- 风险等级必须有可访问的文字标签，不能只靠颜色；
- 数据卡片、表格、抽屉、时间线和状态标签为主要组件；
- 所有页面具有标题、说明、操作区、加载态、空态和错误态。

## 3. 路由元信息

每个受保护路由需要：

```ts
meta: {
  requiresAuth: true,
  title: "现场安全分析",
  roles: ["admin", "project_manager", "safety_officer"]
}
```

路由守卫职责：

1. 检查 access token；
2. 若 token 存在但用户信息为空，调用 `/auth/me`；
3. 检查角色；
4. 无权限进入 `/403`；
5. token 失效时清理状态并进入 `/login`。

## 4. 状态管理

### `auth` store

保存：

- access token；
- refresh token（若实现）；
- 当前用户；
- 登录状态；
- 登录、注册、登出、恢复会话方法。

### `project` store

保存：

- 项目列表；
- 当前项目；
- 选择项目方法。

### `safety` store

保存：

- 当前分析任务；
- 分析中状态；
- 最近结果；
- 错误信息。

## 5. Axios 约定

统一在 `src/api/http.ts`：

- `baseURL` 从 `VITE_API_BASE_URL` 读取；
- 请求头自动添加 Bearer token；
- 401 清理登录状态；
- 统一提取后端错误；
- 上传接口超时时间可设为 120 秒；
- 普通接口超时 30 秒。

统一响应：

```ts
export interface ApiEnvelope<T> {
  success: boolean
  message: string
  data: T
  request_id: string
}
```

## 6. 页面详细设计

### 6.1 登录页

字段：

- 用户名；
- 密码；
- 记住登录；
- 登录按钮；
- 注册入口；
- 演示账号快速填充。

演示账号：

- `manager / BuildWise123!`
- `safety / BuildWise123!`
- `quality / BuildWise123!`
- `worker / BuildWise123!`

### 6.2 注册页

字段：

- 用户名；
- 姓名；
- 密码；
- 确认密码；
- 角色；
- 手机号（可选）。

前端校验：

- 用户名 3–32 字符；
- 密码至少 8 字符；
- 两次密码一致；
- 不允许选择管理员。

### 6.3 工作台

数据卡片：

- 今日新增隐患；
- 高风险隐患；
- 待整改工单；
- 待复查工单；
- 本周关闭率；
- 当前项目人数。

图表：

- 最近 7 天隐患趋势；
- 风险等级分布；
- 工单状态分布。

列表：

- 最近安全分析；
- 临近截止工单。

### 6.4 安全分析页

左侧输入：

- 当前项目；
- 图片拖拽上传；
- 施工位置；
- 作业类型；
- 现场说明；
- 开始分析。

右侧结果：

- 原图/标注图切换；
- 综合风险等级；
- 隐患列表；
- 每条隐患的置信度和框；
- 规范依据；
- 工单草稿；
- 工友提醒；
- Agent 执行轨迹；
- `AI 模拟结果` 或 `真实模型结果` 标记；
- `需要人工复核` 标记；
- “确认创建工单”按钮。

禁止在分析接口调用成功后自动创建正式工单。必须由用户确认。

### 6.5 安全历史页

- 按日期、项目、风险等级筛选；
- 表格显示任务编号、时间、位置、风险、隐患数、模式；
- 点击进入详情或复用结果组件；
- MVP 可只实现列表和详情抽屉。

### 6.6 工单列表

筛选：

- 状态；
- 风险等级；
- 责任人；
- 项目；
- 截止日期。

表格：

- 编号；
- 标题；
- 位置；
- 风险；
- 责任人；
- 截止时间；
- 状态；
- 操作。

### 6.7 工单详情

- 基本信息；
- 隐患原图；
- 规范依据；
- 整改要求；
- 复查要求；
- 状态时间线；
- 状态变更；
- 备注；
- 整改图片上传（MVP 可先保留接口和控件）。

### 6.8 工友助手

MVP：

- 文本输入；
- 三个快捷问题；
- 对话列表；
- 响应中状态；
- 答案来源或“模板回答”标记。

语音按钮存在但显示“下一阶段接入”。

### 6.9 日报

- 日期选择；
- 项目选择；
- 统计卡片；
- 日报正文；
- 生成/刷新；
- 打印；
- PDF 导出按钮占位或实现浏览器打印。

### 6.10 质量巡检、绿色建造

使用统一 `ModulePlaceholder`：

- 模块名称；
- Agent 名称；
- 状态：规划中；
- 计划能力；
- 计划输入；
- 计划输出；
- 当前已完成的接口或数据结构。

### 6.11 规范知识库

MVP：

- 展示内置规范条目；
- 支持关键词搜索；
- 显示来源、条款、分类和正文；
- 文档上传按钮可显示“后续版本”。

## 7. TypeScript 核心类型

```ts
export type RiskLevel = "normal" | "low" | "medium" | "high" | "critical"

export type WorkOrderStatus =
  | "pending"
  | "in_progress"
  | "pending_review"
  | "closed"

export interface Hazard {
  id: string
  hazard_type: string
  hazard_name: string
  description: string
  confidence: number
  risk_level: RiskLevel
  bbox?: [number, number, number, number]
}

export interface Evidence {
  id?: string
  source: string
  article: string
  content: string
  score?: number
}

export interface AgentTraceItem {
  agent: string
  status: "pending" | "running" | "completed" | "failed" | "skipped"
  message: string
  started_at?: string
  finished_at?: string
  duration_ms?: number
}

export interface SafetyAnalysisResult {
  task_id: string
  project_id: string
  upload_id: string
  risk_level: RiskLevel
  hazards: Hazard[]
  evidence: Evidence[]
  work_order_draft: WorkOrderDraft | null
  worker_message: string
  report_preview: string
  agent_trace: AgentTraceItem[]
  review_required: boolean
  is_simulated: boolean
  provider_info: Record<string, string>
}
```

## 8. 前端验收

- 所有页面路由可以访问；
- 未实现页面有正式占位内容；
- 登录状态刷新后保留；
- 无权限路由被拦截；
- 安全分析可以上传图片并展示全量结果；
- 工单确认后可以在列表中看到；
- 状态变更后页面立即更新；
- 前端生产构建成功；
- 不存在 TypeScript 错误；
- 不存在控制台未处理异常。


---

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


---

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


---

# 06 Agent 与算法设计文档

## 1. 总体原则

五个 Agent 在 MVP 中是 LangGraph 的确定性业务节点，不是五个自由聊天机器人。

```text
SafetyAgent
  → RagAgent
  → WorkOrderAgent
  → WorkerCareAgent
  → ReportAgent
```

如果没有隐患：

```text
SafetyAgent
  → ReportAgent（生成“今日未发现新增隐患”的预览）
  → END
```

## 2. 共享状态

```python
class WorkflowState(TypedDict, total=False):
    task_id: str
    project_id: str
    upload_id: str
    image_path: str
    location: str
    work_type: str
    description: str
    requested_by: str

    hazards: list[dict]
    risk_level: str
    evidence: list[dict]
    work_order_draft: dict | None
    worker_message: str
    report_preview: str

    agent_trace: list[dict]
    review_required: bool
    is_simulated: bool
    provider_info: dict[str, str]
    errors: list[dict]
```

每个节点只返回自己更新的字段。

## 3. Provider 抽象

### VisionProvider

```python
class VisionProvider(Protocol):
    def analyze(self, image_path: str, context: dict) -> VisionResult:
        ...
```

### RetrievalProvider

```python
class RetrievalProvider(Protocol):
    def search(self, query: str, filters: dict, top_k: int) -> list[Evidence]:
        ...
```

### TextProvider

```python
class TextProvider(Protocol):
    def generate_worker_message(self, payload: dict) -> str:
        ...

    def generate_report(self, payload: dict) -> str:
        ...
```

## 4. SafetyAgent

### 4.1 MVP 模式

`MockVisionProvider` 根据显式 `demo_scenario` 返回结果：

- `no_helmet`；
- `missing_guardrail`；
- `normal`。

若未传 `demo_scenario`，使用默认 `no_helmet`，并强制返回：

```json
{
  "is_simulated": true,
  "provider": "mock"
}
```

不得伪装为真实图像识别。

### 4.2 真实视觉模式

推荐后续采用：

```text
YOLO 目标检测
  → person / helmet / vest / guardrail
  → 人员与 PPE 空间关联
  → 风险规则
  → 可选多模态模型复核复杂场景
```

### 4.3 人员与安全帽关联

对每个人员框，定义头部区域为人员框上部 35%。若安全帽中心落在头部区域，则视为匹配。

```python
head_bottom = person_y1 + 0.35 * (person_y2 - person_y1)
matched = (
    person_x1 <= helmet_center_x <= person_x2
    and person_y1 <= helmet_center_y <= head_bottom
)
```

需要处理多个安全帽和多个人员，使用距离或 IoU 进行一对一贪心匹配。

### 4.4 风险规则

示例：

```python
RISK_RULES = {
    "no_helmet": {
        "risk_level": "high",
        "base_score": 90,
        "assignee_role": "safety_officer",
        "deadline_hours": 4
    },
    "missing_guardrail": {
        "risk_level": "critical",
        "base_score": 98,
        "assignee_role": "project_manager",
        "deadline_hours": 2
    },
    "no_safety_vest": {
        "risk_level": "medium",
        "base_score": 65,
        "assignee_role": "safety_officer",
        "deadline_hours": 24
    }
}
```

综合风险等级取最高等级，不取平均。

### 4.5 输出

- hazards；
- risk_level；
- review_required=true；
- 标注图相对 URL；
- provider 信息；
- trace。

## 5. RagAgent

### 5.1 MVP 本地检索

使用 `safety_standards.json`，每条结构：

```json
{
  "id": "STD-HELMET-001",
  "category": "个人防护",
  "hazard_types": ["no_helmet"],
  "source": "项目安全生产管理制度",
  "article": "第12条",
  "content": "进入施工现场的人员应正确佩戴安全帽。",
  "keywords": ["安全帽", "个人防护", "施工现场"]
}
```

检索评分：

```text
hazard_type 精确匹配：+5
标题/分类关键词命中：每个 +2
正文关键词命中：每个 +1
```

按分数排序，返回 Top 3。低于最小分数不返回。

### 5.2 Chroma 模式

后续实现：

- 文档按条款切分；
- 元数据保存来源、条款、类别和适用风险；
- 向量召回 Top K；
- 可加关键词重排；
- 返回原文，不让 LLM 编造条款。

### 5.3 无依据处理

若无足够依据：

- `evidence=[]`；
- 写入 trace；
- `review_required=true`；
- 工单注明“规范依据待人工补充”；
- 禁止生成虚构条款。

## 6. WorkOrderAgent

### 6.1 硬字段由规则生成

- 工单 ID；
- 风险等级；
- 状态；
- 责任角色；
- 截止时间；
- 项目；
- 位置；
- 来源任务；
- 是否人工确认。

### 6.2 软字段

MVP 由模板生成：

- 标题；
- 问题描述；
- 整改要求；
- 复查要求。

后续 LLM 必须使用结构化输出并由 Pydantic 校验。

### 6.3 工单草稿

Agent 只生成草稿，不直接创建正式工单。正式工单由 `POST /work-orders` 创建。

## 7. WorkerCareAgent

### 7.1 目标

把专业整改要求转成尊重、简短、明确的工友提醒。

规则：

- 不超过 100 个中文字符；
- 高风险必须出现“暂停作业”；
- 不训斥；
- 不添加处罚、责任或未提供的法规；
- 明确下一步动作；
- 返回纯文本。

模板示例：

```text
师傅，请先暂停一下作业。请正确戴好安全帽并扣紧下颌带，
待安全员确认后再继续施工。
```

## 8. ReportAgent

### 8.1 统计由 SQL 完成

统计：

- 今日隐患总数；
- 各风险等级数量；
- 各工单状态数量；
- 今日新建和关闭数量；
- 临近截止工单；
- 高频隐患类型。

### 8.2 文本生成

MVP 用模板；LLM 模式只负责组织语言，输入为结构化统计，禁止修改数字。

日报结构：

1. 今日巡检概况；
2. 主要风险；
3. 整改进度；
4. 待协调事项；
5. 明日重点。

## 9. LangGraph 路由

```python
START -> safety

if hazards:
    safety -> rag -> work_order -> worker_care -> report -> END
else:
    safety -> report -> END
```

节点异常策略：

- 视觉失败：整个任务失败；
- RAG 失败：继续生成工单，但标记依据待补充；
- WorkerCare 失败：使用本地模板；
- Report 失败：使用本地模板；
- 所有异常进入 trace 和 agent_runs.error_message。

## 10. 执行轨迹

每个节点写：

```json
{
  "agent": "RagAgent",
  "status": "completed",
  "message": "检索到 2 条规范依据",
  "started_at": "...",
  "finished_at": "...",
  "duration_ms": 43
}
```

## 11. 安全边界

- 所有结果标记为辅助建议；
- 工程结论必须人工复核；
- 置信度不等于法规符合性；
- 模拟结果必须显式标注；
- 无依据时不得编造；
- 工单必须人工确认；
- 日报数字必须来源于数据库。


---

# 07 测试与验收文档

## 1. 后端测试

必须至少覆盖：

### 认证

- 注册成功；
- 用户名重复失败；
- 登录成功；
- 密码错误失败；
- 未登录访问保护接口返回 401；
- 角色无权限返回 403。

### 安全工作流

- `no_helmet` 场景完整经过五个节点；
- `normal` 场景跳过 RAG、工单和工友节点；
- 返回 trace 顺序正确；
- `is_simulated=true`；
- 文件记录创建；
- agent_run、incident 写库。

### 工单

- 草稿确认后创建正式工单；
- 重复确认阻止或幂等；
- 合法状态流转；
- 非法状态流转失败；
- 工友无法变更工单。

### 日报

- 统计数字与数据库一致；
- 同项目同日期生成时更新而非重复；
- 无数据时生成空日报。

### 知识库

- 关键词搜索能命中安全帽条款；
- 未命中返回空数组而不是伪造。

## 2. 前端验收

- `npm run build` 成功；
- TypeScript 无错误；
- 所有路由存在；
- 所有菜单可点击；
- 登录、注册、退出正常；
- 安全分析展示完整结果；
- 工单确认和状态变更正常；
- 占位页面内容完整；
- 401 自动跳登录；
- 403 页面正常。

## 3. 端到端验收脚本

1. 启动后端并执行迁移、种子；
2. 启动前端；
3. 使用 `safety` 账号登录；
4. 进入安全分析；
5. 选择演示项目；
6. 上传任意合法图片；
7. 选择 `no_helmet` 演示场景；
8. 确认显示：
   - 高风险；
   - 1 项未戴安全帽；
   - 至少 1 条规范；
   - 工单草稿；
   - 工友提醒；
   - 五节点轨迹；
9. 点击确认工单；
10. 在工单列表中查看；
11. 状态改为整改中；
12. 使用项目经理账号改为待复查、已关闭；
13. 打开日报并刷新；
14. 确认统计变化；
15. 点击质量和绿色页面，确认占位正常。

## 4. Definition of Done

Codex 只有在以下全部完成后才能结束：

- 完整目录生成；
- 数据库迁移成功；
- 种子数据成功；
- 后端测试通过；
- 前端构建通过；
- 核心 E2E 流程可执行；
- README 包含完整启动命令；
- `.env.example` 完整；
- 不提交真实密钥；
- 真实和模拟结果有明确标记；
- 所有页面存在；
- 所有 API 文档可在 Swagger 查看；
- 最终输出实施摘要和未实现项。


---

# 08 启动、部署与运维文档

## 1. 本地启动

### 后端

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

访问：

- 前端：`http://localhost:5173`
- Swagger：`http://localhost:8000/docs`

## 2. 一键开发脚本

Codex 需要提供：

- `scripts/dev.ps1`：Windows 下同时启动前后端；
- `scripts/dev.sh`：Unix 下同时启动前后端；
- 脚本不能静默吞掉错误。

## 3. Docker Compose

至少包含：

- backend；
- frontend；
- 可选 postgres profile。

默认可继续使用 SQLite 挂载卷。前端生产镜像由 Nginx 提供静态文件，并反向代理 `/api`。

## 4. README 必须包含

- 项目介绍；
- 技术架构；
- 目录说明；
- 环境要求；
- 本地启动；
- Docker 启动；
- 演示账号；
- 主 Demo 脚本；
- 模拟模式说明；
- 真实 YOLO、Chroma、LLM 的切换方式；
- 测试命令；
- 常见问题；
- 人工复核边界。

## 5. 生产注意事项

- 更换 `SECRET_KEY`；
- 使用 PostgreSQL；
- 关闭 DEBUG；
- 限制 CORS；
- 使用对象存储；
- 使用 HTTPS；
- 增加速率限制；
- 使用后台任务处理较慢模型；
- 使用集中式日志；
- 数据和模型许可需要人工确认。


---

# 09 Codex 最终交付清单

Codex 最终应交付：

- 完整可运行仓库；
- 前端所有页面和路由；
- 后端全部路由骨架；
- 真实注册登录与权限；
- SQLite 数据库及 Alembic；
- 五 Agent 最小闭环；
- 工单持久化和状态机；
- 日报真实统计；
- 规范本地检索；
- 演示数据；
- 测试；
- README；
- Docker Compose；
- 一键开发脚本。

真实 YOLO、Chroma、LLM 可以作为适配器保留，但默认不要求密钥或模型权重。
