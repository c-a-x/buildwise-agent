# BuildWise Warm Operations UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有 Vue 前端所有路由统一为参考 `warm-dashboard-template` 的暖色运营台视觉，同时保留现有 API、状态和安全闭环行为。

**Architecture:** 以 `frontend/src/assets/main.css` 作为全局 token、布局和共享组件样式的唯一入口，重构 `MainLayout`、`AppSidebar`、`AppTopbar` 的壳层，再按页面类型收敛现有 view 的局部样式。尽量复用已有 Vue 组件和 SVG `AppIcon`，不引入大型 UI 框架或修改后端。

**Tech Stack:** Vue 3, TypeScript, Vite, Vue Router, Pinia, CSS variables, Vitest, vue-tsc.

---

### Task 1: Replace the global visual foundation

**Files:**
- Modify: `frontend/src/assets/main.css`
- Review: `frontend/src/assets/styles/reset.css`, `frontend/src/assets/styles/variables.css`, `frontend/src/assets/styles/global.css`

- [ ] **Step 1: Record the baseline verification**

Run from `frontend`:

```powershell
npm run type-check
npm run test:unit -- --run
npm run build-only
```

Expected: all existing checks pass or their current failure is recorded before CSS changes.

- [ ] **Step 2: Replace global tokens and base rules**

Set the warm operations tokens from the design spec (`#f7f6f1` canvas, `#10233d` navigation, `#0f6e70` primary, semantic risk colors), the Chinese system font stack, 8px spacing rhythm, 8/12/16px radii, and visible focus styles. Keep the existing class names used by views so business markup remains unchanged.

- [ ] **Step 3: Add shared interaction and responsive rules**

Keep interactive controls at least 44px high, add `cursor: pointer`, stable hover/pressed states, `prefers-reduced-motion`, 375/768/1024/1440 breakpoints, `overflow-x: auto` only on table wrappers, and prevent page-level horizontal overflow.

- [ ] **Step 4: Verify the global stylesheet does not leave duplicate token sources**

Run:

```powershell
rg -n "--bg|--primary|--navy-900|@media|prefers-reduced-motion" src/assets/main.css src/assets/styles
```

Expected: the active token definitions live in `main.css`; legacy files are not imported twice and no new raw screen-level color token is introduced.

---

### Task 2: Rebuild the application shell

**Files:**
- Modify: `frontend/src/layouts/MainLayout.vue`
- Modify: `frontend/src/components/layout/AppSidebar.vue`
- Modify: `frontend/src/components/layout/AppTopbar.vue`
- Modify: `frontend/src/components/layout/UserMenu.vue`
- Modify: `frontend/src/stores/app.ts`

- [ ] **Step 1: Preserve existing shell behaviors**

Keep sidebar collapse state, project loading, route-based active state, auth-based nav filtering, user menu actions, and the existing toast notice behavior.

- [ ] **Step 2: Apply the warm shell structure**

Render the brand block, grouped navigation, offline simulated-provider status, topbar project selector, provider status, notifications, user menu, and a skip link targeting `#main-content`. Keep `aria-current="page"`, semantic `<nav>`, and `main tabindex="-1"`.

- [ ] **Step 3: Add mobile drawer behavior without changing routes**

At widths below 1024px, render the sidebar as an off-canvas drawer controlled by the existing app store state. Add a scrim and close action with an accessible label; reserve content padding so the drawer never hides the first page section.

- [ ] **Step 4: Run layout and router tests**

```powershell
npm run test:unit -- --run src/router/__tests__/guards.spec.ts
npm run type-check
```

Expected: router guard behavior remains unchanged and TypeScript has no new errors.

---

### Task 3: Normalize shared components and status language

**Files:**
- Modify: `frontend/src/components/common/AppPageHeader.vue`
- Modify: `frontend/src/components/common/AppState.vue`
- Modify: `frontend/src/components/common/AppLoading.vue`
- Modify: `frontend/src/components/common/AppEmpty.vue`
- Modify: `frontend/src/components/common/AppError.vue`
- Modify: `frontend/src/components/dashboard/MetricCard.vue`
- Modify: `frontend/src/components/dashboard/RiskTrendChart.vue`
- Modify: `frontend/src/components/dashboard/WorkOrderStatusChart.vue`
- Modify: `frontend/src/components/safety/AgentTrace.vue`
- Modify: `frontend/src/components/work-order/WorkOrderStatusTag.vue`
- Modify: `frontend/src/components/report/ReportMetrics.vue`
- Modify: `frontend/src/components/common/ModulePlaceholder.vue`

- [ ] **Step 1: Align shared card, header, state, and button classes**

Use semantic token classes and one elevation scale. Keep all existing props and emitted events; only change markup when needed for heading hierarchy, status text, or accessibility labels.

- [ ] **Step 2: Make risk and run-mode states explicit**

Render risk text plus an icon and semantic class for normal/low/medium/high/critical. Render `模拟`, `真实`, `草稿，需人工确认`, and `需要人工复核` as visible labels rather than color-only treatments.

- [ ] **Step 3: Make loading, empty, and error states actionable**

Use skeleton or progress feedback for async states; empty states include a next action; error states include the cause when available and a retry action when the component already exposes one.

- [ ] **Step 4: Run existing component and view tests**

```powershell
npm run test:unit -- --run src/components src/views/__tests__/placeholderViews.spec.ts
```

Expected: component props, emitted events, and placeholder states remain compatible.

---

### Task 4: Restyle authentication and error surfaces

**Files:**
- Modify: `frontend/src/layouts/AuthLayout.vue`
- Modify: `frontend/src/views/auth/LoginView.vue`
- Modify: `frontend/src/views/auth/RegisterView.vue`
- Modify: `frontend/src/views/auth/ForgotPasswordView.vue`
- Modify: `frontend/src/views/error/ForbiddenView.vue`
- Modify: `frontend/src/views/error/NotFoundView.vue`

- [ ] **Step 1: Preserve form fields, validation, demo account shortcuts, and route transitions**

Do not change auth API calls or validation rules. Keep visible labels, autocomplete attributes, password visibility controls, error placement, and demo account actions.

- [ ] **Step 2: Apply the split warm-brand layout**

Use a warm visual brand panel with construction/AI copy and a focused white form panel; hide only the decorative panel on narrow screens. Keep a single primary submit action and visible focus states.

- [ ] **Step 3: Verify auth view tests and type-check**

```powershell
npm run test:unit -- --run src/views/__tests__
npm run type-check
```

Expected: all auth and error views render with their existing test selectors and no TypeScript errors.

---

### Task 5: Restyle the overview and project management pages

**Files:**
- Modify: `frontend/src/views/dashboard/DashboardView.vue`
- Modify: `frontend/src/views/projects/ProjectListView.vue`
- Modify: `frontend/src/views/HomeView.vue`
- Modify: `frontend/src/views/AboutView.vue`

- [ ] **Step 1: Reorder the dashboard into the warm template hierarchy**

Keep the SQL-backed metrics and chart data; present an operations hero, six metrics, risk trend, risk distribution, work-order status, and recent task list. Add chart legends/text summaries without replacing the current data sources.

- [ ] **Step 2: Restyle project cards and about content**

Use warm surface cards, restrained construction imagery/gradients, clear progress and status labels, and consistent page headers. Do not add new project fields or fake API data.

- [ ] **Step 3: Verify dashboard view tests**

```powershell
npm run test:unit -- --run src/views/__tests__/dashboardView.spec.ts
```

Expected: existing metric and route assertions pass.

---

### Task 6: Restyle the safety, work-order, and worker-care loop

**Files:**
- Modify: `frontend/src/views/safety/SafetyAnalysisView.vue`
- Modify: `frontend/src/views/safety/RealtimeMonitorView.vue`
- Modify: `frontend/src/views/safety/SafetyHistoryView.vue`
- Modify: `frontend/src/views/work-orders/WorkOrderListView.vue`
- Modify: `frontend/src/views/work-orders/WorkOrderDetailView.vue`
- Modify: `frontend/src/views/worker-care/WorkerCareView.vue`
- Modify: `frontend/src/views/wellbeing/WellbeingView.vue`
- Modify: `frontend/src/components/safety/*.vue`
- Modify: `frontend/src/components/work-order/*.vue`

- [ ] **Step 1: Preserve the safety result data flow**

Keep upload, simulated/real provider labels, detection image toggle, hazards, evidence, worker message, agent trace, and manual work-order confirmation. Do not auto-create a formal work order after analysis.

- [ ] **Step 2: Apply the high-signal analysis layout**

Use a 5/7 split for input and result, a dark media stage for marked images/video, warm cards for evidence and draft work orders, and an amber review banner that says `AI 草稿，需要人工复核`.

- [ ] **Step 3: Apply consistent list/detail patterns**

Use filter toolbar, risk badges with text/icon, deadline emphasis, responsive tables/cards, and a timeline with status labels. Keep audio/voice actions visibly marked as simulated or next-stage where the current backend is not real.

- [ ] **Step 4: Run the loop tests**

```powershell
npm run test:unit -- --run src/views/__tests__/safetyAnalysisView.spec.ts src/views/__tests__/SafetyHistoryView.spec.ts src/views/__tests__/workOrderList.spec.ts src/views/__tests__/workerCareView.spec.ts
```

Expected: upload, result, history, work-order, and worker-care assertions pass without API changes.

---

### Task 7: Restyle reports, knowledge, modules, and administration pages

**Files:**
- Modify: `frontend/src/views/reports/DailyReportView.vue`
- Modify: `frontend/src/views/reports/ReportHistoryView.vue`
- Modify: `frontend/src/views/knowledge/KnowledgeBaseView.vue`
- Modify: `frontend/src/views/quality/QualityInspectionView.vue`
- Modify: `frontend/src/views/green/GreenConstructionView.vue`
- Modify: `frontend/src/views/user/UserProfileView.vue`
- Modify: `frontend/src/views/audit/AuditLogView.vue`
- Modify: `frontend/src/views/system/SystemSettingsView.vue`

- [ ] **Step 1: Use reading-first layouts for reports and knowledge**

Keep report dates, project selection, SQL-derived metrics, print/export actions, knowledge search, category filters, clause source, and score fields. Use a high-contrast reading surface and visible source metadata.

- [ ] **Step 2: Give quality and green modules formal product surfaces**

Keep their existing placeholder/status APIs and render module status, planned capabilities, planned inputs/outputs, and current interface coverage inside the same card system. Do not invent standards or metrics.

- [ ] **Step 3: Normalize admin forms and audit tables**

Use visible labels, grouped settings, danger separation for destructive actions, compact audit tables, and clear permission/status tags.

- [ ] **Step 4: Run the remaining view tests**

```powershell
npm run test:unit -- --run src/views/__tests__/dailyReportView.spec.ts src/views/__tests__/knowledgeBaseView.spec.ts src/views/__tests__/auditLogView.spec.ts src/views/__tests__/systemSettingsView.spec.ts
```

Expected: report, knowledge, audit, and settings behavior remains intact.

---

### Task 8: Accessibility, responsive, and final verification pass

**Files:**
- Modify: `frontend/src/assets/main.css`
- Modify: the specific view/component files listed in Tasks 2–7 when a verification check identifies a UI or accessibility regression
- Review: all files modified by Tasks 1–7

- [ ] **Step 1: Audit interactive labels, focus, and contrast**

Run:

```powershell
rg -n "button|aria-label|role=|tabindex|risk-badge|status-pill|is_simulated|review_required" src
```

Confirm icon-only controls have labels, risk and simulation states have text, and no new clickable element relies on hover alone.

- [ ] **Step 2: Run all frontend tests and build**

```powershell
npm run test:unit -- --run
npm run type-check
npm run build
```

Expected: Vitest passes, `vue-tsc` passes, and Vite produces a production bundle.

- [ ] **Step 3: Inspect the final diff**

```powershell
git diff --stat
git diff --check
git status --short
```

Expected: only UI/spec/plan files are changed, no generated dependency directory is staged, and whitespace checks pass.

- [ ] **Step 4: Commit the implementation**

```powershell
git add frontend/src docs/superpowers/plans/2026-08-08-buildwise-warm-operations-ui.md
git commit -m "feat: unify warm operations UI"
```
