import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { authGuard } from './guards'

const publicRoutes: RouteRecordRaw[] = [
  { path: '/login', name: 'login', component: () => import('@/views/auth/LoginView.vue'), meta: { title: '登录' } },
  { path: '/register', name: 'register', component: () => import('@/views/auth/RegisterView.vue'), meta: { title: '注册' } },
  { path: '/forgot-password', name: 'forgot-password', component: () => import('@/views/auth/ForgotPasswordView.vue'), meta: { title: '找回密码' } },
]

const protectedRoutes: RouteRecordRaw[] = [
  { path: '/dashboard', name: 'dashboard', component: () => import('@/views/dashboard/DashboardView.vue'), meta: { requiresAuth: true, title: '项目工作台' } },
  { path: '/projects', name: 'projects', component: () => import('@/views/projects/ProjectListView.vue'), meta: { requiresAuth: true, title: '项目管理' } },
  { path: '/safety/analyze', name: 'safety-analyze', component: () => import('@/views/safety/SafetyAnalysisView.vue'), meta: { requiresAuth: true, title: '现场安全分析', roles: ['admin', 'project_manager', 'safety_officer'] } },
  { path: '/safety/realtime', name: 'safety-realtime', component: () => import('@/views/safety/RealtimeMonitorView.vue'), meta: { requiresAuth: true, title: '实时监控', roles: ['admin', 'project_manager', 'safety_officer'] } },
  { path: '/safety/history', name: 'safety-history', component: () => import('@/views/safety/SafetyHistoryView.vue'), meta: { requiresAuth: true, title: '安全历史', roles: ['admin', 'project_manager', 'safety_officer', 'quality_inspector'] } },
  { path: '/work-orders', name: 'work-orders', component: () => import('@/views/work-orders/WorkOrderListView.vue'), meta: { requiresAuth: true, title: '整改工单' } },
  { path: '/work-orders/:id', name: 'work-order-detail', component: () => import('@/views/work-orders/WorkOrderDetailView.vue'), meta: { requiresAuth: true, title: '工单详情' } },
  { path: '/worker-care', name: 'worker-care', component: () => import('@/views/worker-care/WorkerCareView.vue'), meta: { requiresAuth: true, title: '工友助手' } },
  { path: '/worker-wellbeing', name: 'worker-wellbeing', component: () => import('@/views/wellbeing/WellbeingView.vue'), meta: { requiresAuth: true, title: '工友关怀' } },
  { path: '/reports/daily', name: 'daily-report', component: () => import('@/views/reports/DailyReportView.vue'), meta: { requiresAuth: true, title: '项目日报', roles: ['admin', 'project_manager', 'safety_officer', 'quality_inspector'] } },
  { path: '/reports/history', name: 'report-history', component: () => import('@/views/reports/ReportHistoryView.vue'), meta: { requiresAuth: true, title: '日报历史', roles: ['admin', 'project_manager', 'safety_officer', 'quality_inspector'] } },
  { path: '/quality', name: 'quality', component: () => import('@/views/quality/QualityInspectionView.vue'), meta: { requiresAuth: true, title: '质量巡检', roles: ['admin', 'project_manager', 'safety_officer', 'quality_inspector'] } },
  { path: '/green', name: 'green', component: () => import('@/views/green/GreenConstructionView.vue'), meta: { requiresAuth: true, title: '绿色建造' } },
  { path: '/knowledge', name: 'knowledge', component: () => import('@/views/knowledge/KnowledgeBaseView.vue'), meta: { requiresAuth: true, title: '规范知识库' } },
  { path: '/profile', name: 'profile', component: () => import('@/views/user/UserProfileView.vue'), meta: { requiresAuth: true, title: '用户中心' } },
  { path: '/settings', name: 'settings', component: () => import('@/views/system/SystemSettingsView.vue'), meta: { requiresAuth: true, title: '系统设置', roles: ['admin', 'project_manager'] } },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/', component: () => import('@/layouts/AuthLayout.vue'), children: publicRoutes },
    { path: '/', component: () => import('@/layouts/MainLayout.vue'), children: protectedRoutes },
    { path: '/403', name: 'forbidden', component: () => import('@/views/error/ForbiddenView.vue'), meta: { title: '无权限' } },
    { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/views/error/NotFoundView.vue'), meta: { title: '页面不存在' } },
  ],
})

router.beforeEach(authGuard)

export default router
