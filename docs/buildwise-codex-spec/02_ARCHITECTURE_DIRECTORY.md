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
