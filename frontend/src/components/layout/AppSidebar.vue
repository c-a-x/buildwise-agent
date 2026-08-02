<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import AppIcon, { type IconName } from '@/components/common/AppIcon.vue'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'

interface NavigationItem { label: string; to: string; icon: IconName; roles?: string[] }
interface NavigationGroup { label: string; items: NavigationItem[] }

const app = useAppStore()
const auth = useAuthStore()
const route = useRoute()

const groups: NavigationGroup[] = [
  { label: '总览', items: [{ label: '项目工作台', to: '/dashboard', icon: 'dashboard' }, { label: '项目管理', to: '/projects', icon: 'project' }] },
  { label: '安全闭环', items: [{ label: '现场安全分析', to: '/safety/analyze', icon: 'shield', roles: ['admin', 'project_manager', 'safety_officer'] }, { label: '安全历史', to: '/safety/history', icon: 'history', roles: ['admin', 'project_manager', 'safety_officer', 'quality_inspector'] }, { label: '整改工单', to: '/work-orders', icon: 'clipboard' }, { label: '工友助手', to: '/worker-care', icon: 'worker' }] },
  { label: '项目协同', items: [{ label: '项目日报', to: '/reports/daily', icon: 'report' }, { label: '日报历史', to: '/reports/history', icon: 'history' }, { label: '规范知识库', to: '/knowledge', icon: 'book' }] },
  { label: '规划模块', items: [{ label: '质量巡检', to: '/quality', icon: 'quality' }, { label: '绿色建造', to: '/green', icon: 'leaf' }] },
]

const visibleGroups = computed(() => groups.map((group) => ({ ...group, items: group.items.filter((item) => !item.roles || (auth.user && item.roles.includes(auth.user.role))) })).filter((group) => group.items.length))
const isActive = (to: string): boolean => route.path === to || route.path.startsWith(`${to}/`)
</script>

<template>
  <aside class="sidebar" :class="{ collapsed: app.sidebarCollapsed }">
    <div class="brand-block">
      <div class="brand-mark" aria-hidden="true"><i /><i /><i /></div>
      <div class="brand-copy"><strong>筑智共生</strong><small>BUILDWISE AI AGENT</small></div>
    </div>
    <nav class="sidebar-nav" aria-label="主导航">
      <div v-for="group in visibleGroups" :key="group.label" class="nav-group">
        <p class="nav-group-title">{{ group.label }}</p>
        <RouterLink v-for="item in group.items" :key="item.to" :to="item.to" class="nav-item" :class="{ active: isActive(item.to) }" :aria-current="isActive(item.to) ? 'page' : undefined">
          <AppIcon :name="item.icon" :size="18" /><span>{{ item.label }}</span>
        </RouterLink>
      </div>
    </nav>
    <div class="sidebar-foot"><div class="system-status"><span class="status-dot online" /><div><strong>离线模拟 Provider</strong><small>无需外部 API Key</small></div></div></div>
  </aside>
</template>
