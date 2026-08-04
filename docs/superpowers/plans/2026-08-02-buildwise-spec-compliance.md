# BuildWise Specification Compliance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不破坏当前可运行 MVP 的前提下，使 BuildWise AI Agent 与 `docs/buildwise-codex-spec/PROJECT_SPEC_FULL.md` 及 01–08 分册逐项对齐，并完成可复现的自动化验收。

**Architecture:** 保留现有 Vue 3 + Pinia + FastAPI + SQLAlchemy 分层。将 Provider 选择集中到工厂，将五 Agent 迁移到显式的 LangGraph 状态图；HTTP 仍只调用 Service，Agent 不接触 HTTP 或数据库。前端补齐历史任务恢复、检测框、工单详情和筛选能力；文档、资产、启动脚本和测试作为独立可验收工作流收尾。

**Tech Stack:** Vue 3、TypeScript、Vite、Vue Router、Pinia、Axios、Vitest、FastAPI、Pydantic v2、SQLAlchemy 2、Alembic、JWT、pytest、httpx/TestClient、LangGraph；默认 Provider 仍为 MockVision、LocalKeyword、Template。

---

## 0. 当前基线与决策

当前已经存在并通过验证的能力：登录/注册、项目访问控制、图片上传、五 Agent 离线闭环、RAG 证据、人工确认工单、四状态流转、日报 SQL 统计、质量/绿色占位、主要前端路由、13 个后端测试、前端 TypeScript 检查和生产构建。

本计划只处理规格偏差，不重写已经稳定的业务闭环。严格对齐需要处理以下问题：

- `data_demo/images/` 中缺少规格要求的两个演示图片；
- `router/guards.ts` 和独立 `modules.py` 缺失，当前逻辑合并在其他文件；
- 当前工作流是自定义顺序执行，未使用 LangGraph；
- Provider 适配器存在，但 `BuildWiseWorkflow` 直接硬编码 Mock/Local/Template，环境变量不能真正切换 Provider；
- 安全历史链接没有加载 `?task=` 详情，工单详情没有返回/显示原图和规范证据，检测结果没有显示 bbox；
- 工单列表缺少责任人和截止日期筛选，安全分析没有真正的拖拽上传；
- README 缺少环境要求、真实 Provider 切换、常见问题和完整 Demo 说明，健康检查链接错误；
- 测试没有覆盖无数据日报、重复确认幂等、附件持久化及安全分析数据库写入的全部验收条目。

## 1. 文件地图

### 规格与资源

- `docs/buildwise-codex-spec/PROJECT_SPEC_FULL.md`：完整约束基线；
- `docs/buildwise-codex-spec/01_PRODUCT_REQUIREMENTS.md`：产品闭环、角色、页面；
- `docs/buildwise-codex-spec/02_ARCHITECTURE_DIRECTORY.md`：目录和依赖方向；
- `docs/buildwise-codex-spec/04_BACKEND_API_SPEC.md`：API、权限、配置；
- `docs/buildwise-codex-spec/05_DATABASE_DESIGN.md`：表结构、状态和一致性；
- `docs/buildwise-codex-spec/06_AGENT_ALGORITHM_DESIGN.md`：五 Agent、Provider、路由；
- `docs/buildwise-codex-spec/07_TEST_ACCEPTANCE.md`：测试与 Definition of Done；
- `docs/buildwise-codex-spec/08_DEPLOYMENT_AND_RUNBOOK.md`：启动、Docker、README 要求；
- `data_demo/images/`、`data_demo/standards/`：离线演示资产。

### 后端

- `backend/app/core/config.py`：环境变量和 Provider 配置；
- `backend/app/providers/`：视觉、检索、文本适配器；
- `backend/app/workflow/`：共享状态、路由和工作流图；
- `backend/app/services/safety_service.py`：上传、工作流、分析结果持久化；
- `backend/app/services/work_order_service.py`：人工确认、状态机、审计；
- `backend/app/api/v1/endpoints/`：HTTP 参数、鉴权、Service 编排；
- `backend/app/models/entities.py`、`backend/alembic/versions/`：模型和迁移；
- `backend/tests/`：后端验收测试。

### 前端

- `frontend/src/router/index.ts`、新增 `frontend/src/router/guards.ts`：路由与鉴权守卫；
- `frontend/src/views/safety/`：分析和历史；
- `frontend/src/views/work-orders/`：列表和详情；
- `frontend/src/components/safety/`：图片、bbox、隐患、证据和 Agent trace；
- `frontend/src/api/`、`frontend/src/types/`：API 和类型；
- `frontend/src/components/__tests__/`、`frontend/src/views/`：Vitest 与页面行为测试。

## 2. 实施顺序与交付门槛

按以下顺序执行，每个阶段都必须独立可运行：

1. 结构、资产和 API 文档基线；
2. Provider 工厂和 LangGraph 工作流；
3. 后端结果完整性、附件、权限和审计；
4. 前端历史恢复、检测可视化、工单详情和筛选；
5. README、启动脚本和 Docker 校验；
6. 测试补齐、端到端验收和最终规格矩阵。

每个阶段结束时执行：

```powershell
cd E:\cc项目\buildwise-agent\backend
..\backend\venv\Scripts\python.exe -m pytest -q

cd E:\cc项目\buildwise-agent\frontend
npm run type-check
npm run build
```

## 3. Task 1：补齐规格目录、演示资产和路由拆分

**Files:**

- Create: `data_demo/images/safety_no_helmet.jpg`
- Create: `data_demo/images/safety_normal.jpg`
- Create: `frontend/src/assets/images/.gitkeep`
- Create: `frontend/src/router/guards.ts`
- Create: `backend/app/api/v1/endpoints/modules.py`
- Modify: `frontend/src/router/index.ts`
- Modify: `backend/app/api/v1/endpoints/health.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/test_structure.py`

- [x] **Step 1: 生成两个真实的合法图片资产**

使用项目允许的图片生成方式，生成尺寸至少为 640×480 的 JPEG；`safety_no_helmet.jpg` 应展示一个用于离线演示的未戴安全帽场景，`safety_normal.jpg` 应展示无明显隐患场景。文件名必须保持规格原名，不能用空文件或文本伪装成图片。

验证：

```powershell
python -c "from PIL import Image; Image.open('data_demo/images/safety_no_helmet.jpg').verify(); Image.open('data_demo/images/safety_normal.jpg').verify(); print('DEMO_IMAGES_OK')"
```

Expected: 输出 `DEMO_IMAGES_OK`。

- [x] **Step 2: 将路由守卫从路由表中抽出**

在 `frontend/src/router/guards.ts` 中实现唯一的守卫函数，保持当前行为：恢复 token 对应用户、未登录跳转 `/login?redirect=...`、角色不匹配跳转 `/403`、已登录访问登录/注册跳转 `/dashboard`。

```ts
import type { NavigationGuard } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { Role } from '@/types/api'

export const authGuard: NavigationGuard = async (to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth) {
    if (!auth.user && auth.token) await auth.restoreSession()
    if (!auth.isAuthenticated) return { name: 'login', query: { redirect: to.fullPath } }
    if (to.meta.roles && !to.meta.roles.includes(auth.user?.role as Role)) return { name: 'forbidden' }
  }
  if ((to.name === 'login' || to.name === 'register') && auth.isAuthenticated) return { name: 'dashboard' }
}
```

在 `index.ts` 中删除内联函数，改为 `router.beforeEach(authGuard)`；路由 meta 保持原有标题和角色限制。

- [x] **Step 3: 将模块状态接口拆成独立 endpoint**

把当前 `health.py` 中的 `/modules` 移到 `modules.py`，保留响应字段 `key/name/agent_name/status/description/planned_inputs/planned_outputs/available_endpoints`。`health.py` 只保留 `/health`。两个 router 都必须通过 `/api/v1` 注册，不能删除现有接口。

- [x] **Step 4: 写结构回归测试**

在 `backend/tests/test_structure.py` 中验证：两个图片可被 PIL 打开、`/api/v1/health` 和 `/api/v1/modules` 返回 200、返回的模块集合仍包含 `safety/quality/green`。前端路由守卫用静态检查确认 `router.beforeEach(authGuard)` 存在。

- [x] **Step 5: 运行本任务验证**

```powershell
cd E:\cc项目\buildwise-agent\backend
..\backend\venv\Scripts\python.exe -m pytest tests/test_structure.py -q
```

Expected: 新增测试全部通过，且已有测试无回归。

## 4. Task 2：实现 Provider 工厂并将五 Agent 接入 LangGraph

**Files:**

- Create: `backend/app/providers/factory.py`
- Create: `backend/app/workflow/graph_builder.py`
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/providers/vision/ultralytics.py`
- Modify: `backend/app/providers/retrieval/chroma.py`
- Modify: `backend/app/providers/text/openai_compatible.py`
- Modify: `backend/app/workflow/graph.py`
- Modify: `backend/app/workflow/routing.py`
- Modify: `backend/app/services/safety_service.py`
- Modify: `backend/.env.example`
- Test: `backend/tests/test_providers.py`
- Test: `backend/tests/test_safety_workflow.py`

- [x] **Step 1: 扩充配置对象并定义合法 Provider 值**

在 `Settings` 增加 `llm_base_url`、`llm_api_key`、`llm_model`、`vision_model_path`，保留现有默认值。Provider 名称只允许：

```python
VISION_PROVIDER_VALUES = {"mock", "ultralytics"}
RETRIEVAL_PROVIDER_VALUES = {"local_keyword", "chroma"}
TEXT_PROVIDER_VALUES = {"template", "openai_compatible"}
```

启动时只校验名称；只有请求选择了非默认 Provider 时才加载可选依赖，确保默认离线启动不需要模型或密钥。

- [x] **Step 2: 实现集中式 Provider 工厂**

`backend/app/providers/factory.py` 只负责根据 `Settings` 创建 Provider，不创建数据库会话：

```python
def build_vision_provider(settings: Settings) -> VisionProvider:
    if settings.vision_provider == "mock":
        return MockVisionProvider()
    if settings.vision_provider == "ultralytics":
        return UltralyticsVisionProvider(model_path=settings.vision_model_path)
    raise AppError("不支持的视觉 Provider", "PROVIDER_NOT_SUPPORTED", 500)
```

检索和文本工厂采用同样的分支。非默认 Provider 缺少依赖或配置时抛出可识别的 `PROVIDER_NOT_CONFIGURED`，不能静默回退到 Mock。

- [x] **Step 3: 将可选适配器改为可配置的真实调用边界**

`UltralyticsVisionProvider` 使用 lazy import 加载 YOLO 模型；`ChromaRetrievalProvider` 使用 `settings.chroma_dir` 初始化持久化索引；`OpenAICompatibleTextProvider` 使用 `LLM_BASE_URL/LLM_API_KEY/LLM_MODEL` 调用兼容接口。所有实现继续返回现有 Protocol 的字段，不改变 Agent 输入输出。

真实 Provider 无法启动时，错误必须包含配置项名称和切换回离线模式的命令，例如：

```text
VISION_PROVIDER=mock
RETRIEVAL_PROVIDER=local_keyword
TEXT_PROVIDER=template
```

- [x] **Step 4: 用 LangGraph 显式表达路由**

在 `graph_builder.py` 中建立共享 `WorkflowState` 的 `StateGraph`：

```python
graph = StateGraph(WorkflowState)
graph.add_node("safety", safety_agent.run)
graph.add_node("rag", rag_agent.run)
graph.add_node("work_order", work_order_agent.run)
graph.add_node("worker_care", worker_care_agent.run)
graph.add_node("report", report_agent.run)
graph.set_entry_point("safety")
graph.add_conditional_edges("safety", route_after_safety, {"hazards": "rag", "normal": "report"})
graph.add_edge("rag", "work_order")
graph.add_edge("work_order", "worker_care")
graph.add_edge("worker_care", "report")
graph.add_edge("report", END)
```

每个 Agent 仍只返回自己的字段和 trace；`graph.py` 负责合并状态、注入 Provider 信息和统一 `review_required/is_simulated`。不允许在节点内调用 FastAPI 或 SQLAlchemy。

- [x] **Step 5: 写 Provider 和路由测试**

`test_providers.py` 必须覆盖：默认三种 Provider 的类型、未知 Provider 的错误、非默认 Provider 缺少配置的明确错误。`test_safety_workflow.py` 继续断言 `no_helmet` 五节点和 `normal` 跳过中间节点，且 trace 顺序不变。

- [x] **Step 6: 运行本任务验证**

```powershell
cd E:\cc项目\buildwise-agent\backend
..\backend\venv\Scripts\python.exe -m pytest tests/test_providers.py tests/test_safety_workflow.py -q
```

Expected: 默认模式离线通过；切换到未配置真实 Provider 时返回明确配置错误，不发生静默模拟。

## 5. Task 3：补齐安全分析结果、工单详情、附件和状态一致性

**Files:**

- Create: `backend/alembic/versions/0002_result_payload_and_attachment.py`
- Modify: `backend/app/models/entities.py`
- Modify: `backend/app/services/safety_service.py`
- Modify: `backend/app/services/work_order_service.py`
- Modify: `backend/app/api/v1/endpoints/work_orders.py`
- Modify: `backend/app/schemas/work_order.py`
- Modify: `backend/app/utils/files.py`
- Modify: `frontend/src/types/workOrder.ts`
- Modify: `frontend/src/api/workOrders.ts`
- Modify: `frontend/src/views/safety/SafetyAnalysisView.vue`
- Modify: `frontend/src/views/work-orders/WorkOrderDetailView.vue`
- Test: `backend/tests/test_safety_persistence.py`
- Test: `backend/tests/test_work_order_integrity.py`

- [x] **Step 1: 持久化完整分析结果**

给 `AgentRun` 增加 `result_json` JSON 字段，用 Alembic 迁移而不是 `create_all` 追表。`SafetyService.analyze()` 在 commit 前保存 `worker_message`、`report_preview` 和 `work_order_draft`，`get_task()` 直接恢复这些字段，保证刷新历史详情后仍能看到完整结果。

```python
task.result_json = {
    "work_order_draft": state.get("work_order_draft"),
    "worker_message": state.get("worker_message", ""),
    "report_preview": state.get("report_preview", ""),
}
```

- [x] **Step 2: 让工单详情返回原图、标注图和规范证据**

在 `work_order_dict()` 中根据 `incident.upload_id` 组装受控 `/storage/...` URL，并查询 `IncidentEvidence`。新增响应字段：

```python
{
    "file_url": "/storage/uploads/...",
    "annotated_url": "/storage/annotated/...",
    "evidence": [{"source": "...", "article": "...", "content": "...", "score": 1.0}],
}
```

绝不返回本机绝对路径。

- [x] **Step 3: 持久化整改附件**

复用 `save_upload()` 保存附件，创建 `Upload` 记录，并在 `WorkOrderEvent.attachment_upload_id` 写入附件 ID。`POST /work-orders/{id}/attachments` 返回 `upload_id/file_url/size_bytes`；只允许 JPEG、PNG、WEBP，沿用 10 MB 限制。

- [x] **Step 4: 完善工单状态和幂等规则**

保留现有允许状态：

```python
VALID_TRANSITIONS = {
    "pending": {"in_progress"},
    "in_progress": {"pending_review"},
    "pending_review": {"in_progress", "closed"},
    "closed": set(),
}
```

同一 `incident_id` 存在活动工单时，确认接口返回原工单；关闭时必须写 `closed_at`、事件和审计日志；特殊回退只有管理员/项目经理在提供备注时允许。

- [x] **Step 5: 前端显示工单来源证据和图片**

在 `WorkOrder` 类型加入 `file_url/annotated_url/evidence`，详情页加入原图、规范依据和整改附件上传状态；附件控件成功后刷新时间线。

- [x] **Step 6: 写一致性回归测试**

测试必须断言：

- 分析后 `uploads/agent_runs/incidents/incident_evidences` 均有记录；
- 历史任务返回完整草稿、工友提醒和日报预览；
- 重复确认返回同一正式工单；
- 非法状态失败；
- 关闭写 `closed_at` 和事件；
- 附件写入 Upload 与事件关联。

- [x] **Step 7: 运行迁移和本任务测试**

```powershell
cd E:\cc项目\buildwise-agent\backend
..\backend\venv\Scripts\python.exe -m alembic upgrade head
..\backend\venv\Scripts\python.exe -m pytest tests/test_safety_persistence.py tests/test_work_order_integrity.py -q
```

Expected: 迁移成功，所有一致性断言通过。

## 6. Task 4：补齐前端安全分析、历史和工单验收

**Files:**

- Create: `frontend/src/components/safety/BoundingBoxOverlay.vue`
- Modify: `frontend/src/components/safety/DetectionPreview.vue`
- Modify: `frontend/src/components/safety/HazardList.vue`
- Modify: `frontend/src/views/safety/SafetyAnalysisView.vue`
- Modify: `frontend/src/views/safety/SafetyHistoryView.vue`
- Modify: `frontend/src/views/work-orders/WorkOrderListView.vue`
- Modify: `frontend/src/views/work-orders/WorkOrderDetailView.vue`
- Modify: `frontend/src/api/workOrders.ts`
- Modify: `frontend/src/types/workOrder.ts`
- Test: `frontend/src/components/__tests__/BoundingBoxOverlay.spec.ts`
- Test: `frontend/src/views/__tests__/SafetyHistoryView.spec.ts`

- [x] **Step 1: 实现真正的拖拽上传**

在安全分析页的上传区域增加 `dragover/drop/dragleave` 事件，统一调用：

```ts
function acceptFile(candidate: File | undefined): void {
  if (!candidate || !['image/jpeg', 'image/png', 'image/webp'].includes(candidate.type)) {
    localError.value = '仅支持 JPEG、PNG、WEBP 图片'
    return
  }
  file.value = candidate
  previewUrl.value = URL.createObjectURL(candidate)
  safety.clearResult()
}
```

保留现有文件选择器和大小校验。

- [x] **Step 2: 显示置信度和 bbox**

新增 `BoundingBoxOverlay.vue`，约定 bbox 为 0–1 归一化坐标，使用百分比定位：

```vue
<span
  v-for="hazard in hazards"
  :key="hazard.id"
  class="detection-box"
  :style="{
    left: `${hazard.bbox?.[0] * 100}%`,
    top: `${hazard.bbox?.[1] * 100}%`,
    width: `${(hazard.bbox?.[2] - hazard.bbox?.[0]) * 100}%`,
    height: `${(hazard.bbox?.[3] - hazard.bbox?.[1]) * 100}%`,
  }"
>
  {{ hazard.hazard_name }} · {{ Math.round(hazard.confidence * 100) }}%
</span>
```

空 bbox 不绘制框，但仍显示隐患文本和置信度；颜色之外必须保留文字风险标签。

- [x] **Step 3: 使历史任务链接可用**

`SafetyHistoryView` 继续跳转 `/safety/analyze?task=<task_id>`，`SafetyAnalysisView` 在 `onMounted` 读取 query，调用 `safetyApi.task(taskId)` 并把返回内容写入 store。历史查看模式隐藏上传提交或显示“重新分析”操作，不能要求用户再次上传图片。

- [x] **Step 4: 完善工单列表筛选**

API 查询参数增加 `assignee_user_id/deadline_from/deadline_to`；前端增加责任人和截止日期控件，并保持状态、风险、项目筛选。筛选变化后重新请求，不在前端伪造分页数据。

- [x] **Step 5: 完善工单详情**

显示原图/标注图、规范依据、整改和复查要求、状态时间线、备注、附件上传；状态下拉只展示后端允许的下一状态。关闭操作必须在前端要求备注，后端也必须再次校验。

- [x] **Step 6: 写前端回归测试**

Vitest 覆盖 bbox 百分比样式、历史 query 调用详情 API、没有 token 时路由跳转登录、角色不符时跳转 403。测试不依赖真实后端，使用 mock API。

- [x] **Step 7: 运行前端验证**

```powershell
cd E:\cc项目\buildwise-agent\frontend
npm run test:unit -- --run
npm run type-check
npm run build
```

Expected: 所有 Vitest 测试通过，TypeScript 无错误，生产构建成功。

## 7. Task 5：补齐 README、启动脚本和 Docker 运行说明

**Files:**

- Modify: `README.md`
- Modify: `docs/demo-script.md`
- Modify: `docs/api.md`
- Modify: `scripts/dev.ps1`
- Modify: `scripts/dev.sh`
- Modify: `docker-compose.yml`
- Modify: `backend/Dockerfile`
- Modify: `frontend/Dockerfile`
- Test: `scripts/test_runbooks.ps1`

- [x] **Step 1: 修正 README 启动命令和健康检查地址**

README 必须明确：

- Python 3.11+、Node 22+、npm、Docker Compose 环境要求；
- Windows 和 Unix 本地启动；
- 迁移、种子、后端、前端命令；
- 前端 `http://localhost:5173`、Swagger `http://localhost:8000/docs`、健康检查 `http://localhost:8000/api/v1/health`；
- Docker 访问 `http://localhost:8080`。

- [x] **Step 2: 增加 Provider 切换说明**

在 README 加入可复制配置：

```env
VISION_PROVIDER=mock
RETRIEVAL_PROVIDER=local_keyword
TEXT_PROVIDER=template
```

同时说明真实模式需要的模型路径、Chroma 目录、LLM Base URL/API Key/Model，以及默认模式不需要密钥。不得写入真实密钥。

- [x] **Step 3: 增加主 Demo 和常见问题**

README 直接链接 `docs/demo-script.md`，说明从 `safety` 登录到 `no_helmet`、人工确认、项目经理关闭和日报刷新；增加至少四个问题的排查：端口占用、数据库迁移、CORS、Provider 配置错误。

- [x] **Step 4: 修正启动脚本错误可见性**

PowerShell 脚本必须检查后端进程是否立即退出，并将后端 stdout/stderr 重定向到 `backend/storage/logs/dev-backend.log`；前端命令退出时终止后端进程。Bash 脚本保留 `trap`，前后台进程退出时返回非零状态，不能使用 `|| true` 隐藏业务启动错误。

- [x] **Step 5: 校验 Docker 配置**

保持默认 SQLite 卷、Nginx `/api/` 反向代理和 `/storage/` 代理；验证后端镜像能复制根目录 `data_demo`，Compose 环境变量名称与 `Settings` 完全一致。

- [x] **Step 6: 运行 runbook 验证**

```powershell
cd E:\cc项目\buildwise-agent
docker compose config --quiet
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\test_runbooks.ps1
```

Expected: Compose 配置合法，脚本语法、健康检查、迁移和种子命令均返回 0；真实外部 Provider 未配置时只验证错误信息清晰，不要求联网模型成功。

## 8. Task 6：补齐规格测试矩阵和端到端验收

**Files:**

- Create: `backend/tests/test_acceptance_matrix.py`
- Create: `scripts/e2e_demo.py`
- Create: `frontend/src/router/__tests__/guards.spec.ts`
- Modify: `backend/tests/test_auth.py`
- Modify: `backend/tests/test_reports.py`
- Modify: `backend/tests/test_work_orders.py`
- Modify: `backend/tests/test_safety_workflow.py`
- Modify: `README.md`
- Modify: `docs/demo-script.md`

- [x] **Step 1: 覆盖认证验收条目**

补充断言：未登录保护接口返回 401、错误密码失败、重复用户名失败、非管理员注册角色可用、管理员角色注册被拒绝、登出接口返回成功、刷新 token 返回新 token。

- [x] **Step 2: 覆盖分析持久化验收条目**

断言 `no_helmet` 后数据库有 Upload、AgentRun、Incident、IncidentEvidence；`normal` 后没有 Incident 和正式工单；trace 顺序和 `is_simulated/review_required` 正确。

- [x] **Step 3: 覆盖工单和日报边界**

补充：重复确认幂等、工友不能创建/变更/关闭、非法流转失败、关闭写 `closed_at`、同项目同日期日报更新、无数据日报统计全为 0、日报数字不接受前端传入。

- [x] **Step 4: 编写可重复 API E2E 脚本**

`scripts/e2e_demo.py` 使用 TestClient 或已启动 API，按固定顺序执行：

```text
login(safety)
→ list projects
→ upload data_demo/images/safety_no_helmet.jpg
→ analyze(demo_scenario=no_helmet)
→ assert high/one hazard/evidence/five trace
→ confirm work order
→ pending → in_progress → pending_review
→ login(manager) → closed
→ generate daily report
→ search “安全帽”
→ assert quality/green status
```

脚本遇到任何非预期状态码立即退出非零，并打印 task/order/report ID 方便定位。

- [x] **Step 5: 建立前端验收矩阵**

使用 Vitest 检查所有规划路由、登录恢复、401 清理 token、403 跳转、占位页面字段、工单确认按钮禁用状态和日报打印入口。

- [x] **Step 6: 运行完整验收**

```powershell
cd E:\cc项目\buildwise-agent\backend
..\backend\venv\Scripts\python.exe -m alembic upgrade head
..\backend\venv\Scripts\python.exe -m app.db.seed
..\backend\venv\Scripts\python.exe -m pytest -q

cd E:\cc项目\buildwise-agent\frontend
npm run test:unit -- --run
npm run type-check
npm run build

cd E:\cc项目\buildwise-agent
python scripts\e2e_demo.py
docker compose config --quiet
```

Expected：迁移、种子、后端测试、前端测试、TypeScript、构建、E2E 和 Compose 检查全部返回 0。

## 9. 最终 Definition of Done

- [x] 完整目录与两个演示图片存在；
- [x] `PROJECT_SPEC_FULL.md` 的 API、页面、角色、数据库和 Agent 路由均有实现或明确的占位接口；
- [x] Provider 由环境变量选择，默认离线，非默认配置错误可解释；
- [x] 五 Agent 使用显式状态图，trace 顺序和跳过规则稳定；
- [x] 分析历史刷新后结果完整，bbox/置信度/证据可见；
- [x] 工单确认幂等、状态机和附件持久化正确；
- [x] 日报 SQL 统计和无数据场景通过测试；
- [x] 所有规划路由、403/404、占位页面和菜单通过前端测试；
- [x] README 包含环境要求、启动、Docker、Demo、Provider 切换、常见问题和人工复核边界；
- [x] Windows/Unix 启动脚本不会静默吞错；
- [x] `pytest`、Vitest、TypeScript、生产构建、迁移、种子、E2E 和 Compose 校验全部通过；
- [x] 最终交付摘要明确列出仍需人工提供的真实模型、密钥、模型许可和生产运维配置。

## 11. 实际执行记录

- 后端：`28 passed`；`alembic current` 为 `0002_result_payload_and_attachment (head)`；`pip check` 无破损依赖。
- 前端：`15 passed`；`npm run type-check` 通过；`npm run build` 通过。
- UI/UX：按 `ui-ux-pro-max` 完成设计系统、UX、Vue 栈检索；补齐页面语言/标题、统一 SVG 成功图标、44px 触控区、禁用态反馈和已有的焦点/reduced-motion 约束。
- API E2E：`python scripts\\e2e_demo.py` 通过，覆盖分析、工单、日报、知识库、质量和绿色状态。
- Runbook：`scripts\\test_runbooks.ps1` 通过；`docker compose config --quiet` 通过。
- Docker daemon 当前未运行，因此未执行实际镜像构建/容器启动；Dockerfile 和 Compose 静态配置已校验。

## 10. 建议执行方式

先执行 Task 1、Task 3 和 Task 5，快速消除当前可见的规格偏差；再执行 Task 2 的 Provider/LangGraph 正规化；最后执行 Task 4 和 Task 6 做前后端联调与验收。Task 2 的真实 YOLO、Chroma、LLM 依赖不应阻塞默认离线模式测试。
