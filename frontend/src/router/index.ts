import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import type { Role } from '@/types/api'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    title?: string
    roles?: Role[]
  }
}

const publicRoutes: RouteRecordRaw[] = [
  { path: '/login', name: 'login', component: () => import('@/views/auth/LoginView.vue'), meta: { title: '登录' } },
  { path: '/register', name: 'register', component: () => import('@/views/auth/RegisterView.vue'), meta: { title: '注册' } },
  { path: '/forgot-password', name: 'forgot-password', component: () => import('@/views/auth/ForgotPasswordView.vue'), meta: { title: '找回密码' } },
]

const protectedRoutes: RouteRecordRaw[] = [
  { path: '/dashboard', name: 'dashboard', component: () => import('@/views/dashboard/DashboardView.vue'), meta: { requiresAuth: true, title: '项目工作台' } },
  { path: '/projects', name: 'projects', component: () => import('@/views/projects/ProjectListView.vue'), meta: { requiresAuth: true, title: '项目管理' } },
  { path: '/safety/analyze', name: 'safety-analyze', component: () => import('@/views/safety/SafetyAnalysisView.vue'), meta: { requiresAuth: true, title: '现场安全分析', roles: ['admin', 'project_manager', 'safety_officer'] } },
  { path: '/safety/history', name: 'safety-history', component: () => import('@/views/safety/SafetyHistoryView.vue'), meta: { requiresAuth: true, title: '安全历史', roles: ['admin', 'project_manager', 'safety_officer', 'quality_inspector'] } },
  { path: '/work-orders', name: 'work-orders', component: () => import('@/views/work-orders/WorkOrderListView.vue'), meta: { requiresAuth: true, title: '整改工单' } },
  { path: '/work-orders/:id', name: 'work-order-detail', component: () => import('@/views/work-orders/WorkOrderDetailView.vue'), meta: { requiresAuth: true, title: '工单详情' } },
  { path: '/worker-care', name: 'worker-care', component: () => import('@/views/worker-care/WorkerCareView.vue'), meta: { requiresAuth: true, title: '工友助手' } },
  { path: '/reports/daily', name: 'daily-report', component: () => import('@/views/reports/DailyReportView.vue'), meta: { requiresAuth: true, title: '项目日报', roles: ['admin', 'project_manager', 'safety_officer', 'quality_inspector'] } },
  { path: '/reports/history', name: 'report-history', component: () => import('@/views/reports/ReportHistoryView.vue'), meta: { requiresAuth: true, title: '日报历史', roles: ['admin', 'project_manager', 'safety_officer', 'quality_inspector'] } },
  { path: '/quality', name: 'quality', component: () => import('@/views/quality/QualityInspectionView.vue'), meta: { requiresAuth: true, title: '质量巡检' } },
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

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth) {
    if (!auth.user && auth.token) await auth.restoreSession()
    if (!auth.isAuthenticated) return { name: 'login', query: { redirect: to.fullPath } }
    if (to.meta.roles && !to.meta.roles.includes(auth.user?.role as Role)) return { name: 'forbidden' }
  } else if ((to.name === 'login' || to.name === 'register') && auth.isAuthenticated) {
    return { name: 'dashboard' }
  }
})

export default router
