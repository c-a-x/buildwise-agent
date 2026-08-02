<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import AppIcon from '@/components/common/AppIcon.vue'
import { useAppStore } from '@/stores/app'
import { useProjectStore } from '@/stores/project'
import UserMenu from './UserMenu.vue'

const app = useAppStore()
const projects = useProjectStore()
const route = useRoute()
const pageTitle = computed(() => String(route.meta.title || '项目工作台'))

function selectProject(event: Event): void {
  projects.selectProject((event.target as HTMLSelectElement).value)
}
</script>

<template>
  <header class="topbar">
    <div class="topbar-left"><button class="icon-button" type="button" aria-label="折叠侧边栏" @click="app.toggleSidebar"><AppIcon name="menu" :size="18" /></button><div><p class="breadcrumb">BuildWise / {{ pageTitle }}</p><strong>{{ pageTitle }}</strong></div></div>
    <div class="topbar-right">
      <label class="project-select" aria-label="当前项目"><AppIcon name="project" :size="15" /><select :value="projects.currentProject?.id" @change="selectProject"><option v-for="project in projects.projects" :key="project.id" :value="project.id">{{ project.name }}</option></select></label>
      <button class="icon-button notification-button" type="button" aria-label="通知"><AppIcon name="bell" :size="18" /><span class="notification-dot" /></button>
      <UserMenu />
    </div>
  </header>
</template>
