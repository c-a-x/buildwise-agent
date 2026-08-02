<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { dashboardApi, type DashboardSummary } from '@/api/dashboard'
import { getApiError } from '@/api/http'
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageHeader from '@/components/common/AppPageHeader.vue'
import AppState from '@/components/common/AppState.vue'
import { useProjectStore } from '@/stores/project'
import { formatDateTime } from '@/utils/date'
import { riskLabel, statusLabel } from '@/utils/risk'

const projects = useProjectStore()
const summary = ref<DashboardSummary | null>(null)
const loading = ref(false)
const error = ref('')
const metrics = computed(() => summary.value?.metrics ?? { today_incidents: 0, high_risk_incidents: 0, pending_work_orders: 0, pending_review_work_orders: 0, weekly_close_rate: 0, project_members: 0 })
const trendPoints = computed(() => {
  const values = summary.value?.risk_trend ?? []
  const max = Math.max(1, ...values.map((item) => item.count))
  const width = 650
  return values.map((item, index) => `${values.length === 1 ? 0 : (index / (values.length - 1)) * width},${188 - (item.count / max) * 160}`).join(' ')
})
const totalRisk = computed(() => (summary.value?.risk_distribution ?? []).reduce((total, item) => total + item.count, 0))

async function load(): Promise<void> {
  const projectId = projects.currentProject?.id
  if (!projectId) return
  loading.value = true
  error.value = ''
  try { summary.value = await dashboardApi.summary(projectId) } catch (cause) { error.value = getApiError(cause) } finally { loading.value = false }
}

onMounted(load)
watch(() => projects.currentProjectId, load)
</script>

<template>
  <div>
    <AppPageHeader eyebrow="PROJECT CONTROL CENTER" title="项目工作台" :description="projects.currentProject ? `${projects.currentProject.name} · ${projects.currentProject.address}` : '正在载入项目数据'">
      <template #actions><RouterLink class="primary-button" to="/safety/analyze"><AppIcon name="plus" :size="16" />开始安全分析</RouterLink><RouterLink class="secondary-button" to="/reports/daily"><AppIcon name="report" :size="16" />查看今日日报</RouterLink></template>
    </AppPageHeader>
    <div v-if="error" class="alert alert-error" role="alert">{{ error }}</div>
    <div class="metrics-grid" aria-label="项目关键指标">
      <article class="metric-card"><div class="metric-top"><span class="metric-icon danger"><AppIcon name="shield" :size="18" /></span><span class="metric-delta">今日</span></div><strong>{{ metrics.today_incidents }}</strong><p>今日新增隐患</p></article>
      <article class="metric-card"><div class="metric-top"><span class="metric-icon warning"><AppIcon name="spark" :size="18" /></span><span class="metric-delta">需关注</span></div><strong>{{ metrics.high_risk_incidents }}</strong><p>高风险隐患</p></article>
      <article class="metric-card"><div class="metric-top"><span class="metric-icon"><AppIcon name="clipboard" :size="18" /></span><span class="metric-delta">处理中</span></div><strong>{{ metrics.pending_work_orders }}</strong><p>待整改工单</p></article>
      <article class="metric-card"><div class="metric-top"><span class="metric-icon success"><AppIcon name="check" :size="18" /></span><span class="metric-delta">本周</span></div><strong>{{ metrics.weekly_close_rate }}%</strong><p>工单关闭率 · {{ metrics.project_members }} 位项目成员</p></article>
    </div>
    <AppState v-if="loading && !summary" type="loading" title="正在同步工作台" description="正在从数据库读取项目统计。" />
    <div v-else class="dashboard-grid">
      <section class="card chart-card span-2"><div class="card-head"><div><p class="section-kicker">7-DAY TREND</p><h3>隐患趋势</h3></div><span>按天统计 · SQL 数据</span></div><div class="line-chart"><svg viewBox="0 0 650 200" role="img" aria-label="最近七天隐患数量趋势"><polyline :points="trendPoints || '0,188 650,188'" fill="none" stroke="#2c78ff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" /><polyline :points="trendPoints || '0,188 650,188'" fill="none" stroke="#18c4d9" stroke-width="9" stroke-linecap="round" stroke-linejoin="round" opacity=".12" /></svg><div class="x-labels"><span v-for="item in summary?.risk_trend ?? []" :key="item.date">{{ item.date.slice(5) }}</span></div></div></section>
      <section class="card chart-card"><div class="card-head"><div><p class="section-kicker">RISK MIX</p><h3>风险等级分布</h3></div><span>累计</span></div><div class="donut-wrap"><div class="donut"><div class="donut-inner"><strong>{{ totalRisk }}</strong><span>项隐患</span></div></div><div class="legend-list"><p v-for="item in summary?.risk_distribution ?? []" :key="item.risk_level"><i :class="item.risk_level" /><span>{{ riskLabel(item.risk_level) }}</span><b>{{ item.count }}</b></p><p v-if="!summary?.risk_distribution.length" class="muted-copy">暂无数据</p></div></div></section>
      <section class="card span-2"><div class="card-head"><div><p class="section-kicker">RECENT ANALYSIS</p><h3>最近安全分析</h3></div><RouterLink class="button-icon" to="/safety/history">查看全部 <AppIcon name="arrow" :size="14" /></RouterLink></div><div v-if="summary?.recent_tasks.length" class="compact-list"><RouterLink v-for="task in summary.recent_tasks" :key="task.task_id" :to="`/safety/history?task=${task.task_id}`" class="compact-item"><div><strong>{{ task.location }} · {{ task.work_type }}</strong><small>{{ task.task_id }} · {{ formatDateTime(task.created_at) }}</small></div><span :class="`risk-badge ${task.risk_level}`"><i class="risk-dot" />{{ riskLabel(task.risk_level) }}</span></RouterLink></div><AppState v-else title="还没有分析任务" description="上传一张现场图片，开始第一条可追踪的安全闭环。" /></section>
      <section class="card"><div class="card-head"><div><p class="section-kicker">DUE SOON</p><h3>临近截止工单</h3></div><RouterLink class="button-icon" to="/work-orders">查看全部</RouterLink></div><div v-if="summary?.due_work_orders.length" class="compact-list"><RouterLink v-for="order in summary.due_work_orders" :key="order.id" :to="`/work-orders/${order.id}`" class="compact-item"><div><strong>{{ order.title }}</strong><small>{{ formatDateTime(order.deadline) }} · {{ statusLabel(order.status) }}</small></div><span>{{ riskLabel(order.risk_level) }}</span></RouterLink></div><AppState v-else title="暂无临近工单" description="确认一条整改草稿后，责任人与截止时间会出现在这里。" /></section>
    </div>
  </div>
</template>
