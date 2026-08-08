# BuildWise 暖色运营台 UI 设计说明

## 1. 目标与边界

本次改造参考 `warm-dashboard-template` 的暖米白画布、柔和卡片、青绿色主交互色和数据看板层级，并结合 BuildWise 的施工安全、AI Agent 与风险闭环语义，统一现有 Vue 前端全站界面。

改造只涉及前端视觉、布局、响应式行为和可用性反馈：

- 保留现有 Vue 3 + TypeScript + Vite、路由、API、Pinia 状态和业务流程；
- 保留 AI 结果模拟/真实边界、人工确认工单、日报 SQL 统计等既有业务约束；
- 不引入新的大型 UI 框架，不把 Next 模板运行时复制到 Vue 工程；
- 统一现有页面和组件样式，移除本次改造造成的无效样式或重复 token。

## 2. 视觉方向

采用“暖色运营台（Warm Operations Console）”：

- 暖灰白内容画布，承接模板的温度和留白；
- 深海军蓝固定导航，保持建筑企业软件的可靠感；
- 低饱和青绿色作为主交互色，表达协同和闭环；
- 暖琥珀只用于 AI 建议、待复核、进行中等辅助状态；
- 风险色同时使用颜色、图标和文字，禁止只靠颜色传达风险。

### 2.1 颜色 token

```css
--bg: #f7f6f1;
--surface: #fffdf9;
--surface-soft: #f0efe8;
--surface-muted: #e8e8e0;
--text: #1d2a3a;
--text-soft: #455568;
--muted: #5c6b79;
--muted-light: #7a8792;
--line: #d9ded9;
--navy-950: #0b1728;
--navy-900: #10233d;
--navy-850: #18304f;
--primary: #0f6e70;
--primary-soft: #e2f0ee;
--accent: #a85c0a;
--accent-soft: #fff0d9;
--success: #247a59;
--success-bg: #e5f3eb;
--warning: #a85c0a;
--warning-bg: #fff0d9;
--danger: #b43f3f;
--danger-bg: #fde8e5;
--critical: #8f1d2a;
--critical-bg: #f8dfe3;
```

正文使用中文系统字体栈，任务编号、时间戳、Provider 信息使用等宽字体。基础字号 14–16px，正文行高 1.55–1.7；数字使用 tabular figures。

## 3. 应用壳层

- 桌面端侧栏 248px，支持折叠到 76px；顶部工具栏 72px；内容区最大宽度约 1440px；
- 手机端侧栏变为抽屉，保留菜单按钮、项目选择和通知入口；
- 侧栏分组为：总览、安全闭环、质量闭环、绿色闭环、项目协同、系统管理；
- 顶栏统一显示项目切换、离线模拟 Provider 状态、通知、用户菜单；
- 页面统一使用眉标、标题、说明和一个主操作；
- 增加跳过导航链接、可见焦点环、主内容 focus 管理和 icon-only 控件 aria-label；
- 交互动画使用 150–300ms，支持 `prefers-reduced-motion`，不使用布局抖动型 hover。

## 4. 页面模板

| 页面类型 | 结构 |
| --- | --- |
| 工作台 | 今日态势英雄区、指标卡、风险趋势、风险分布、工单状态、最近任务 |
| 列表页 | 页面头部、筛选工具栏、桌面表格、移动端卡片、分页/空态 |
| 分析页 | 输入与上传、分析状态、结果摘要、隐患/证据、工单草稿、Agent 时间线 |
| 详情页 | 状态英雄区、基本信息、图片/证据、整改要求、状态时间线 |
| 报告页 | 日期和项目筛选、统计摘要、正文阅读面、打印/导出操作 |
| 知识库 | 搜索和分类、条款卡片、详情抽屉、来源与条款元信息 |
| 模块页 | 模块状态、计划能力、输入输出、当前接口、下一阶段提示 |
| 认证/错误页 | 品牌说明面板与表单面板；错误页提供明确返回路径 |

所有页面必须有加载、空数据和错误恢复状态。表格在窄屏转为卡片或在受控容器内水平滚动，禁止页面级横向溢出。

## 5. 页面覆盖

- 认证：登录、注册、找回密码；
- 总览：工作台、项目管理；
- 安全闭环：现场安全分析、实时监控、安全历史、整改工单、工单详情；
- 工友协同：工友助手、工友关怀；
- 报告：项目日报、日报历史；
- 预留模块：质量巡检、绿色建造；
- 知识与管理：规范知识库、用户中心、权限审计、系统设置；
- 错误页：403、404。

## 6. 复用组件

优先重构现有组件：`AppPageHeader`、`MetricCard`、`AppState`、`AppIcon`、`AgentTrace`、`EvidenceList`、`WorkOrderTimeline`、`ReportMetrics` 和 `ModulePlaceholder`。统一以下视觉状态：

- `RiskBadge`：normal / low / medium / high / critical，颜色、图标、文字三者同时出现；
- `StatusPill`：success / warning / danger / simulated / real / draft；
- `Card`：统一圆角、边框和阴影层级；
- `PrimaryButton` / `SecondaryButton` / `IconButton`：统一尺寸、焦点、禁用和加载反馈；
- `DataTable`：统一表头、密度、排序和移动端降级；
- `AppState`：loading / empty / error / retry；
- `Toast`：使用 `role=status` 和 3–5 秒自动消退，不抢夺焦点。

图标继续使用现有 `AppIcon` 的 SVG 线性图标体系，统一 1.8px 描边；不新增 emoji 图标。

## 7. 交互与可访问性验收

- 所有主要操作目标区域至少 44×44px，异步按钮显示处理中并阻止重复提交；
- 表单都有可见 label、辅助说明、就近错误和恢复路径；
- 图表显示图例、数值摘要和可读的表格替代信息；
- 正文和状态文本达到 WCAG AA 对比度；
- 键盘顺序与视觉顺序一致，页面切换后焦点进入主内容；
- 关键状态不只依赖颜色；
- 375px、768px、1024px、1440px 宽度下无页面级横向滚动；
- 模拟结果明确标注 `模拟`，AI 工单明确标注 `草稿，需人工确认`；
- 前端类型检查、单元测试和生产构建通过。

