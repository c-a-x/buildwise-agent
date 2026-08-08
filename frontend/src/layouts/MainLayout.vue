<script setup lang="ts">
import { onMounted } from 'vue'

import AppIcon from '@/components/common/AppIcon.vue'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppTopbar from '@/components/layout/AppTopbar.vue'
import { useAppStore } from '@/stores/app'
import { useProjectStore } from '@/stores/project'

const app = useAppStore()
const projects = useProjectStore()
onMounted(() => {
  if (!projects.projects.length) void projects.loadProjects()
})
</script>

<template>
  <div class="app-shell" :class="{ 'sidebar-collapsed': app.sidebarCollapsed, 'mobile-nav-open': app.mobileNavOpen }">
    <a class="skip-link" href="#main-content">跳到主要内容</a>
    <button v-if="app.mobileNavOpen" class="nav-scrim" type="button" aria-label="关闭导航" @click="app.closeMobileNav" />
    <AppSidebar /><div class="workspace"><AppTopbar /><main id="main-content" class="content" tabindex="-1"><RouterView /></main></div>
    <transition name="toast"><div v-if="app.notice" class="toast" role="status"><span class="toast-check"><AppIcon name="check" :size="12" /></span>{{ app.notice }}</div></transition>
  </div>
</template>
