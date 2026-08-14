<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { systemApi, type ProviderCapability } from '@/api/system'
import AppIcon, { type IconName } from '@/components/common/AppIcon.vue'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'

interface NavigationItem { label: string; to: string; icon: IconName; roles?: string[] }
interface NavigationGroup { label: string; items: NavigationItem[] }

const app = useAppStore()
const auth = useAuthStore()
const route = useRoute()

const groups: NavigationGroup[] = [
  { label: '总览', items: [{ label: '项目工作台', to: '/dashboard', icon: 'dashboard' }, { label: '项目管理', to: '/projects', icon: 'project', roles: ['admin', 'project_manager'] }] },
  { label: '安全闭环', items: [{ label: '现场安全分析', to: '/safety/analyze', icon: 'shield', roles: ['admin', 'project_manager', 'safety_officer'] }, { label: '实时监控', to: '/safety/realtime', icon: 'camera', roles: ['admin', 'project_manager', 'safety_officer'] }, { label: '安全历史', to: '/safety/history', icon: 'history', roles: ['admin', 'project_manager', 'safety_officer', 'quality_inspector'] }, { label: '整改工单', to: '/work-orders', icon: 'clipboard' }, { label: '工友助手', to: '/worker-care', icon: 'worker', roles: ['admin', 'project_manager', 'safety_officer', 'worker'] }, { label: '工友关怀', to: '/worker-wellbeing', icon: 'sun', roles: ['admin', 'project_manager', 'safety_officer', 'worker'] }] },
  { label: '质量闭环', items: [{ label: '质量巡检', to: '/quality', icon: 'quality', roles: ['admin', 'project_manager', 'quality_inspector'] }] },
  { label: '绿色闭环', items: [{ label: '绿色建造', to: '/green', icon: 'leaf', roles: ['admin', 'project_manager', 'safety_officer'] }] },
  { label: '项目协同', items: [{ label: '项目日报', to: '/reports/daily', icon: 'report', roles: ['admin', 'project_manager', 'safety_officer', 'quality_inspector'] }, { label: '日报历史', to: '/reports/history', icon: 'history', roles: ['admin', 'project_manager', 'safety_officer', 'quality_inspector'] }, { label: '规范知识库', to: '/knowledge', icon: 'book' }] },
  { label: '系统管理', items: [{ label: '权限审计', to: '/audit', icon: 'lock', roles: ['admin'] }] },
]

const visibleGroups = computed(() => groups.map((group) => ({ ...group, items: group.items.filter((item) => !item.roles || (auth.user && item.roles.includes(auth.user.role))) })).filter((group) => group.items.length))
const isActive = (to: string): boolean => route.path === to || route.path.startsWith(`${to}/`)

// 侧栏底部 Provider 状态：读取 /health 能力状态；模拟 Provider（mock 视觉 / template 文本）功能可用，视为「在线」，仅 not_configured / unavailable 才不计入
const CORE_KEYS = new Set(['vision', 'retrieval', 'text'])
const aiStatus = ref<{ label: string; detail: string; online: boolean }>({ label: '读取状态…', detail: '', online: false })

onMounted(async () => {
  try {
    const runtime = await systemApi.health()
    const core = (Object.values(runtime.capabilities ?? {}) as ProviderCapability[]).filter((capability) => capability && CORE_KEYS.has(capability.key))
    const connected = core.filter((capability) => capability.status !== 'not_configured' && capability.status !== 'unavailable')
    if (connected.length === 0) {
      aiStatus.value = { label: '系统服务正常', detail: '离线能力可用 · 无需外部 Key', online: false }
    } else {
      aiStatus.value = {
        label: connected.length >= 3 ? '系统服务在线' : '系统服务已接入',
        detail: connected.map((capability) => capability.name).join(' · '),
        online: true,
      }
    }
  } catch {
    aiStatus.value = { label: '状态未知', detail: '无法连接后端', online: false }
  }
})
</script>

<template>
  <aside class="sidebar" :class="{ collapsed: app.sidebarCollapsed }">
    <div class="brand-block">
      <img class="sidebar-logo-horizontal" src="/brand/buildwise-logo-transparent.png" alt="BuildWise 筑智共生 AI Agent" width="198" height="68" />
      <div class="brand-logo-mark" aria-hidden="true"><img src="/brand/buildwise-mark.png" alt="" width="40" height="40" /></div>
      <button class="sidebar-close" type="button" aria-label="关闭导航" @click="app.closeMobileNav"><AppIcon name="close" :size="18" /></button>
    </div>
    <nav class="sidebar-nav" aria-label="主导航">
      <div v-for="group in visibleGroups" :key="group.label" class="nav-group">
        <p class="nav-group-title">{{ group.label }}</p>
        <RouterLink v-for="item in group.items" :key="item.to" :to="item.to" class="nav-item" :class="{ active: isActive(item.to) }" :aria-current="isActive(item.to) ? 'page' : undefined" @click="app.closeMobileNav">
          <AppIcon :name="item.icon" :size="18" /><span>{{ item.label }}</span>
        </RouterLink>
      </div>
    </nav>
    <div class="sidebar-foot"><div class="system-status"><span class="status-dot" :class="aiStatus.online ? 'online' : 'muted'" /><div><strong>{{ aiStatus.label }}</strong><small>{{ aiStatus.detail }}</small></div></div></div>
  </aside>
</template>
