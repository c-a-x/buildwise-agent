<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { getApiError } from '@/api/http'
import { reportsApi } from '@/api/reports'
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageHeader from '@/components/common/AppPageHeader.vue'
import AppState from '@/components/common/AppState.vue'
import { useProjectStore } from '@/stores/project'
import type { DailyReport } from '@/types/report'

const projects = useProjectStore()
const reportDate = ref(new Date().toISOString().slice(0, 10))
const report = ref<DailyReport | null>(null)
const loading = ref(false)
const error = ref('')
const metrics = computed(() => report.value?.statistics)

async function generate(): Promise<void> {
  if (!projects.currentProject?.id) return
  loading.value = true
  error.value = ''
  try { report.value = await reportsApi.generate(projects.currentProject.id, reportDate.value) } catch (cause) { error.value = getApiError(cause) } finally { loading.value = false }
}
async function printReport(): Promise<void> { window.print() }
function selectProject(event: Event): void { projects.selectProject((event.target as HTMLSelectElement).value) }
onMounted(async () => { if (!projects.projects.length) await projects.loadProjects(); if (projects.currentProject?.id) await generate() })
watch(() => projects.currentProjectId, () => { void generate() })
</script>

<template>
  <div><AppPageHeader eyebrow="DAILY PROJECT REPORT" title="项目日报" description="日报数字直接来自项目数据库统计，文本由模板 Provider 组织，不允许模型修改数字。"><template #actions><button class="secondary-button" type="button" @click="printReport"><AppIcon name="download" :size="16" />打印 / 导出 PDF</button></template></AppPageHeader><div class="report-layout"><aside class="report-sidebar card"><div class="card-head"><div><p class="section-kicker">REPORT CONTROL</p><h3>生成参数</h3></div><span>SQL source</span></div><div class="form-grid"><div class="form-field"><label for="report-project">项目</label><select id="report-project" :value="projects.currentProject?.id" @change="selectProject"><option v-for="project in projects.projects" :key="project.id" :value="project.id">{{ project.name }}</option></select></div><div class="form-field"><label for="report-date">报告日期</label><input id="report-date" v-model="reportDate" type="date" /></div><button class="primary-button button-block" type="button" :disabled="loading || !projects.currentProject" @click="generate"><AppIcon :name="loading ? 'refresh' : 'report'" :size="16" />{{ loading ? '正在生成…' : '生成 / 刷新日报' }}</button></div><div v-if="error" class="alert alert-error" role="alert" style="margin-top: 16px">{{ error }}</div><div class="mode-note"><AppIcon name="info" :size="16" /><div><strong>统计口径</strong><span>隐患按创建时间，工单按创建/关闭时间计入；同项目同日期会更新既有日报。</span></div></div></aside><main v-if="report" class="card report-paper"><div class="report-paper-head"><div><p class="eyebrow">BUILDWISE / DAILY REPORT</p><h2>{{ projects.currentProject?.name }} · 项目日报</h2><p>{{ reportDate }} · 生成于 {{ report.created_at.slice(11, 16) }}</p></div><span class="report-stamp">{{ report.is_ai_generated ? 'AI TEXT' : 'TEMPLATE TEXT' }}<br />DB VERIFIED</span></div><div class="report-metrics"><div class="report-metric"><strong>{{ metrics?.incident_total ?? 0 }}</strong><small>今日隐患</small></div><div class="report-metric"><strong>{{ metrics?.high_risk_total ?? 0 }}</strong><small>高风险及以上</small></div><div class="report-metric"><strong>{{ metrics?.new_work_orders ?? 0 }}</strong><small>新建工单</small></div><div class="report-metric"><strong>{{ metrics?.closed_work_orders ?? 0 }}</strong><small>今日关闭</small></div></div><div class="report-content">{{ report.content }}</div></main><AppState v-else-if="loading" type="loading" title="正在生成项目日报" /><AppState v-else title="选择日期生成日报" description="日报数字会从数据库实时汇总，并在这里形成可打印的项目简报。" /></div></div>
</template>
