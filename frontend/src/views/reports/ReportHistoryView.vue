<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { getApiError } from '@/api/http'
import { reportsApi } from '@/api/reports'
import AppPageHeader from '@/components/common/AppPageHeader.vue'
import AppState from '@/components/common/AppState.vue'
import { useProjectStore } from '@/stores/project'
import type { DailyReport } from '@/types/report'

const projects = useProjectStore()
const reports = ref<DailyReport[]>([])
const loading = ref(false)
const error = ref('')
async function load(): Promise<void> { if (!projects.currentProject?.id) return; loading.value = true; try { reports.value = await reportsApi.history(projects.currentProject.id) } catch (cause) { error.value = getApiError(cause) } finally { loading.value = false } }
onMounted(async () => { if (!projects.projects.length) await projects.loadProjects(); await load() })
</script>

<template><div><AppPageHeader eyebrow="REPORT ARCHIVE" title="日报历史" description="按项目回看已生成的日报快照和当日统计口径。" /><section class="card"><div v-if="error" class="alert alert-error">{{ error }}</div><AppState v-if="loading" type="loading" title="正在读取日报历史" /><AppState v-else-if="!reports.length" title="暂无历史日报" description="生成第一份项目日报后，历史快照会保存在这里。" /><div v-else class="table-wrap"><table class="data-table"><thead><tr><th>日期</th><th>隐患</th><th>高风险</th><th>新建工单</th><th>关闭工单</th><th>生成方式</th><th /></tr></thead><tbody><tr v-for="report in reports" :key="report.id"><td><strong>{{ report.report_date }}</strong><small class="mono">{{ report.id }}</small></td><td>{{ report.statistics.incident_total }}</td><td>{{ report.statistics.high_risk_total }}</td><td>{{ report.statistics.new_work_orders }}</td><td>{{ report.statistics.closed_work_orders }}</td><td><span class="status-pill success">{{ report.is_ai_generated ? 'AI 文本' : '模板文本' }}</span></td><td class="action-cell"><RouterLink class="button-icon" :to="{ name: 'daily-report', query: { date: report.report_date } }">打开</RouterLink></td></tr></tbody></table></div></section></div></template>
