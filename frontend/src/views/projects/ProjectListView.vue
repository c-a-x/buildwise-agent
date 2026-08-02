<script setup lang="ts">
import { onMounted } from 'vue'

import AppIcon from '@/components/common/AppIcon.vue'
import AppPageHeader from '@/components/common/AppPageHeader.vue'
import AppState from '@/components/common/AppState.vue'
import { useProjectStore } from '@/stores/project'

const projects = useProjectStore()
onMounted(() => { if (!projects.projects.length) void projects.loadProjects() })
</script>

<template>
  <div><AppPageHeader eyebrow="PROJECT PORTFOLIO" title="项目管理" description="查看当前账号可访问的项目、负责人和现场状态。"><template #actions><button class="secondary-button" type="button" disabled><AppIcon name="plus" :size="16" />新建项目 · 后续版本</button></template></AppPageHeader><AppState v-if="projects.loading" type="loading" title="正在加载项目" /><AppState v-else-if="!projects.projects.length" title="暂无可访问项目" description="请联系管理员加入项目成员。" /><div v-else class="project-grid"><article v-for="project in projects.projects" :key="project.id" class="project-card"><div class="project-image"><span>{{ project.status === 'active' ? '进行中' : '已归档' }}</span></div><div class="project-body"><span class="status-pill success">{{ project.code }}</span><h3>{{ project.name }}</h3><p>{{ project.address }}</p><dl><div><dt>项目负责人</dt><dd>{{ project.manager_user_id }}</dd></div><div><dt>项目状态</dt><dd>安全闭环已启用</dd></div></dl><div class="progress"><span /></div><footer class="project-foot"><span>现场数据持续同步</span><RouterLink to="/dashboard" @click="projects.selectProject(project.id)">进入工作台 <AppIcon name="arrow" :size="13" /></RouterLink></footer></div></article></div></div>
</template>
