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
