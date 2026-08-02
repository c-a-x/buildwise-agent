<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import AppIcon from '@/components/common/AppIcon.vue'
import AppPageHeader from '@/components/common/AppPageHeader.vue'
import AppState from '@/components/common/AppState.vue'
import { useProjectStore } from '@/stores/project'
import { useSafetyStore } from '@/stores/safety'
import { formatDateTime } from '@/utils/date'
import { riskLabel, statusLabel } from '@/utils/risk'

const projects = useProjectStore()
const safety = useSafetyStore()
const query = ref('')
const risk = ref('')
const filteredTasks = () => safety.tasks.filter((task) => (!query.value || `${task.task_id} ${task.location} ${task.work_type}`.toLowerCase().includes(query.value.toLowerCase())) && (!risk.value || task.risk_level === risk.value))
onMounted(async () => { if (!projects.projects.length) await projects.loadProjects(); await safety.loadTasks(projects.currentProject?.id) })
watch(() => projects.currentProjectId, (value) => { if (value) void safety.loadTasks(value) })
</script>

<template>
  <div><AppPageHeader eyebrow="SAFETY HISTORY" title="安全分析历史" description="回看项目内每次图片分析的风险等级、执行状态和模拟模式。"><template #actions><RouterLink class="primary-button" to="/safety/analyze"><AppIcon name="plus" :size="16" />新建分析</RouterLink></template></AppPageHeader><section class="card"><div class="table-toolbar"><div><p class="section-kicker">TRACEABLE TASKS</p><h3>分析任务</h3></div><div class="toolbar-filters"><label class="search-field"><AppIcon name="search" :size="15" /><input v-model.trim="query" placeholder="搜索任务、位置或作业类型" /></label><select v-model="risk" aria-label="筛选风险等级"><option value="">全部风险</option><option value="critical">重大风险</option><option value="high">高风险</option><option value="medium">中风险</option><option value="normal">正常</option></select></div></div><AppState v-if="safety.loadingTasks" type="loading" title="正在读取分析历史" /><AppState v-else-if="!filteredTasks().length" title="暂无匹配任务" description="调整筛选条件，或先完成一次现场安全分析。" /><div v-else class="table-wrap"><table class="data-table"><thead><tr><th>任务编号</th><th>时间 / 位置</th><th>风险</th><th>隐患数</th><th>模式</th><th>状态</th><th /></tr></thead><tbody><tr v-for="task in filteredTasks()" :key="task.task_id"><td><strong class="mono">{{ task.task_id }}</strong><small>{{ task.work_type }}</small></td><td><strong>{{ task.location }}</strong><small>{{ formatDateTime(task.created_at) }}</small></td><td><span :class="`risk-badge ${task.risk_level}`"><i class="risk-dot" />{{ riskLabel(task.risk_level) }}</span></td><td>{{ task.incident_count }}</td><td><span class="status-pill dark" style="background: var(--navy-900)">{{ task.is_simulated ? '模拟' : '真实' }}</span></td><td><span :class="`status-pill ${task.status === 'completed' ? 'success' : ''}`">{{ statusLabel(task.status) }}</span></td><td class="action-cell"><RouterLink class="button-icon" :to="`/safety/analyze?task=${task.task_id}`">查看 <AppIcon name="chevron" :size="13" /></RouterLink></td></tr></tbody></table></div></section></div>
</template>
