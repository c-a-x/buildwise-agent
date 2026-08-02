# Stitch 原型生成简报

## 产品

“筑智共生 AI Agent / BuildWise AI Agent”，面向建筑施工项目的企业级 AI 管理平台。

## 设计目标

设计一个可用于比赛演示、同时具有真实企业软件可信度的响应式 Web 后台。重点表达“发现隐患—检索规范—生成工单—提醒工友—形成日报”的 Agent 闭环。

## 风格关键词

```text
enterprise construction AI platform
industrial digitalization
smart construction site
professional dashboard
dark navy sidebar
light content canvas
cyan and blue accents
risk visualization
glass cards used sparingly
clean data tables
agent workflow timeline
```

## 布局

- 左侧固定导航；
- 顶部栏包含项目切换、通知和用户菜单；
- 内容区使用 12 栏网格；
- 桌面端优先，兼顾 1440×900 和 1920×1080；
- 重要操作区固定、层级清楚；
- 不使用过度夸张的霓虹效果。

## 页面

1. 登录页：品牌说明、账号密码、演示账号。
2. 注册页：用户名、姓名、角色、密码。
3. 工作台：指标卡、风险趋势、风险分布、工单状态、近期任务。
4. 现场安全分析：左侧上传和表单，右侧标注图、风险、依据、工单草稿、Agent 轨迹。
5. 安全历史：筛选、表格、详情抽屉。
6. 工单列表：状态筛选、表格、风险标签。
7. 工单详情：原图、隐患、依据、整改要求、状态时间线。
8. 工友助手：聊天界面、快捷问题、语音按钮占位。
9. 项目日报：日期、统计卡片、日报正文、导出。
10. 规范知识库：搜索、分类、条款卡片。
11. 质量巡检占位：计划能力和模块状态。
12. 绿色建造占位：材料清单、碳排图表的未来布局。
13. 用户中心、系统设置、403、404。

## 安全分析页重点

- 图片上传区域；
- 项目、位置、作业类型；
- 原图与检测图切换；
- 风险等级；
- 隐患卡片；
- 规范引用卡片；
- “AI 草稿，需要人工复核”醒目标识；
- 整改工单预览；
- 工友提醒；
- Agent 执行轨迹：
  `SafetyAgent → RagAgent → WorkOrderAgent → WorkerCareAgent → ReportAgent`；
- “确认创建工单”主按钮。

## 颜色语义

- normal：中性灰或绿色；
- low：蓝色；
- medium：橙色；
- high：红色；
- critical：深红色；
- 所有颜色同时配文字和图标。

## 生成要求

请输出完整页面体系、可复用组件和一致的设计系统，而不是只生成单个 Dashboard。
