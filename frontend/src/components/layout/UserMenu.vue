<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import AppIcon from '@/components/common/AppIcon.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const open = ref(false)
const initials = computed(() => auth.user?.real_name.slice(0, 1) || '筑')
const roleLabel = computed(() => ({ admin: '系统管理员', project_manager: '项目经理', safety_officer: '安全员', quality_inspector: '质检员', worker: '工友' })[auth.user?.role || 'worker'])

async function logout(): Promise<void> {
  await auth.logout()
  await router.push('/login')
}
</script>

<template>
  <div class="user-menu-wrap">
    <button class="user-menu" type="button" aria-label="打开用户菜单" :aria-expanded="open" @click="open = !open">
      <span class="avatar">{{ initials }}</span><span class="user-meta"><strong>{{ auth.user?.real_name || '未登录' }}</strong><small>{{ roleLabel }}</small></span><AppIcon name="chevron" :size="15" />
    </button>
    <div v-if="open" class="user-popover">
      <RouterLink to="/profile" @click="open = false"><AppIcon name="user" :size="16" />用户中心</RouterLink>
      <RouterLink to="/settings" @click="open = false"><AppIcon name="settings" :size="16" />系统设置</RouterLink>
      <button type="button" class="popover-danger" @click="logout"><AppIcon name="logout" :size="16" />退出登录</button>
    </div>
  </div>
</template>
