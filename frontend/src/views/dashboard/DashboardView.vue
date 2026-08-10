<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { dashboardApi, type DashboardSummary } from '@/api/dashboard'
import { getApiError } from '@/api/http'
import { statsApi, type AnomalyResult } from '@/api/stats'
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageHeader from '@/components/common/AppPageHeader.vue'
import AppState from '@/components/common/AppState.vue'
import { useAuthStore } from '@/stores/auth'
import { useProjectStore } from '@/stores/project'
import { formatDateTime } from '@/utils/date'
import { riskLabel, statusLabel } from '@/utils/risk'

const projects = useProjectStore()
const auth = useAuthStore()
const role = computed(() => auth.user?.role ?? '')
const canUseSafety = computed(() => ['admin', 'project_manager', 'safety_officer'].includes(role.value))
const canUseReports = computed(() => ['admin', 'project_manager', 'safety_officer', 'quality_inspector'].includes(role.value))
const summary = ref<DashboardSummary | null>(null)
const loading = ref(false)
const error = ref('')
const anomaly = ref<AnomalyResult | null>(null)
const anomalyLoading = ref(false)
const anomalyModule = ref<'safety' | 'quality'>('safety')
const metrics = computed(() => summary.value?.metrics ?? { today_incidents: 0, high_risk_incidents: 0, pending_work_orders: 0, pending_review_work_orders: 0, weekly_close_rate: 0, project_members: 0 })
const trendPoints = computed(() => {
  const values = summary.value?.risk_trend ?? []
  const max = Math.max(1, ...values.map((item) => item.count))
  const width = 650
  return values.map((item, index) => `${values.length === 1 ? 0 : (index / (values.length - 1)) * width},${188 - (item.count / max) * 160}`).join(' ')
})
const totalRisk = computed(() => (summary.value?.risk_distribution ?? []).reduce((total, item) => total + item.count, 0))
const totalWorkOrders = computed(() => (summary.value?.work_order_distribution ?? []).reduce((total, item) => total + item.count, 0))

async function load(): Promise<void> {
  const projectId = projects.currentProject?.id
  if (!projectId) return
  loading.value = true
  error.value = ''
  try { summary.value = await dashboardApi.summary(projectId) } catch (cause) { error.value = getApiError(cause) } finally { loading.value = false }
  await loadAnomaly()
}

async function loadAnomaly(): Promise<void> {
  const projectId = projects.currentProject?.id
  if (!projectId) return
  anomalyLoading.value = true
  try { anomaly.value = await statsApi.anomalies(projectId, anomalyModule.value) } catch { anomaly.value = null } finally { anomalyLoading.value = false }
}

function switchAnomalyModule(module: 'safety' | 'quality'): void {
  if (module === anomalyModule.value) return
  anomalyModule.value = module
  void loadAnomaly()
}

function anomalyBarHeight(count: number): string {
  const max = Math.max(1, ...(anomaly.value?.samples ?? []).map((sample) => sample.count))
  return `${Math.round((count / max) * 100)}%`
}

function workOrderPercentage(count: number): string {
  return `${totalWorkOrders.value ? Math.round((count / totalWorkOrders.value) * 100) : 0}%`
}

onMounted(load)
watch(() => projects.currentProjectId, load)
</script>

<template>
  <div>
    <AppPageHeader eyebrow="PROJECT CONTROL CENTER" title="项目工作台" :description="projects.currentProject ? `${projects.currentProject.name} · ${projects.currentProject.address}` : '正在载入项目数据'">
      <template #actions>
        <RouterLink v-if="canUseSafety" class="primary-button" to="/safety/analyze"><AppIcon name="plus" :size="16" />开始安全分析</RouterLink>
        <RouterLink v-if="canUseReports" class="secondary-button" to="/reports/daily"><AppIcon name="report" :size="16" />查看今日日报</RouterLink>
      </template>
    </AppPageHeader>
    <div v-if="error" class="alert alert-error" role="alert">{{ error }}</div>
    <div class="metrics-grid" aria-label="项目关键指标">
      <article class="metric-card"><div class="metric-top"><span class="metric-icon danger"><AppIcon name="shield" :size="18" /></span><span class="metric-delta">今日</span></div><strong>{{ metrics.today_incidents }}</strong><p>今日新增隐患</p></article>
      <article class="metric-card"><div class="metric-top"><span class="metric-icon warning"><AppIcon name="spark" :size="18" /></span><span class="metric-delta">需关注</span></div><strong>{{ metrics.high_risk_incidents }}</strong><p>高风险隐患</p></article>
      <article class="metric-card"><div class="metric-top"><span class="metric-icon"><AppIcon name="clipboard" :size="18" /></span><span class="metric-delta">处理中</span></div><strong>{{ metrics.pending_work_orders }}</strong><p>待整改工单</p></article>
      <article class="metric-card"><div class="metric-top"><span class="metric-icon warning"><AppIcon name="clock" :size="18" /></span><span class="metric-delta">待复查</span></div><strong>{{ metrics.pending_review_work_orders }}</strong><p>待复查工单</p></article>
      <article class="metric-card"><div class="metric-top"><span class="metric-icon success"><AppIcon name="check" :size="18" /></span><span class="metric-delta">本周</span></div><strong>{{ metrics.weekly_close_rate }}%</strong><p>本周工单关闭率</p></article>
      <article class="metric-card"><div class="metric-top"><span class="metric-icon"><AppIcon name="worker" :size="18" /></span><span class="metric-delta">项目</span></div><strong>{{ metrics.project_members }}</strong><p>当前项目成员</p></article>
    </div>
    <AppState v-if="loading && !summary" type="loading" title="正在同步工作台" description="正在从数据库读取项目统计。" />
    <div v-else class="dashboard-grid">
      <section class="card chart-card span-2"><div class="card-head"><div><p class="section-kicker">7-DAY TREND</p><h3>隐患趋势</h3></div><span>按天统计 · SQL 数据</span></div><div class="line-chart"><svg viewBox="0 0 650 200" role="img" aria-label="最近七天隐患数量趋势"><polyline class="trend-line" :points="trendPoints || '0,188 650,188'" fill="none" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" /><polyline class="trend-glow" :points="trendPoints || '0,188 650,188'" fill="none" stroke-width="9" stroke-linecap="round" stroke-linejoin="round" opacity=".12" /></svg><div class="x-labels"><span v-for="item in summary?.risk_trend ?? []" :key="item.date">{{ item.date.slice(5) }}</span></div></div></section>
      <section class="card chart-card"><div class="card-head"><div><p class="section-kicker">RISK MIX</p><h3>风险等级分布</h3></div><span>累计</span></div><div class="donut-wrap"><div class="donut"><div class="donut-inner"><strong>{{ totalRisk }}</strong><span>项隐患</span></div></div><div class="legend-list"><p v-for="item in summary?.risk_distribution ?? []" :key="item.risk_level"><i :class="item.risk_level" /><span>{{ riskLabel(item.risk_level) }}</span><b>{{ item.count }}</b></p><p v-if="!summary?.risk_distribution.length" class="muted-copy">暂无数据</p></div></div></section>
      <section class="card chart-card"><div class="card-head"><div><p class="section-kicker">WORK ORDER FLOW</p><h3>工单状态</h3></div><span>{{ totalWorkOrders }} 条</span></div><div class="status-bars"><div v-for="item in summary?.work_order_distribution ?? []" :key="item.status" class="status-bar-row"><div><span>{{ statusLabel(item.status) }}</span><b>{{ item.count }}</b></div><div class="status-bar-track"><span :style="{ width: workOrderPercentage(item.count) }" /></div></div><p v-if="!summary?.work_order_distribution.length" class="muted-copy">暂无工单状态数据</p></div></section>
      <section class="card span-2"><div class="card-head"><div><p class="section-kicker">RECENT ANALYSIS</p><h3>最近安全分析</h3></div><RouterLink class="button-icon" to="/safety/history">查看全部 <AppIcon name="arrow" :size="14" /></RouterLink></div><div v-if="summary?.recent_tasks.length" class="compact-list"><RouterLink v-for="task in summary.recent_tasks" :key="task.task_id" :to="`/safety/history?task=${task.task_id}`" class="compact-item"><div><strong>{{ task.location }} · {{ task.work_type }}</strong><small>{{ task.task_id }} · {{ formatDateTime(task.created_at) }}</small></div><span :class="`risk-badge ${task.risk_level}`"><i class="risk-dot" />{{ riskLabel(task.risk_level) }}</span></RouterLink></div><AppState v-else title="还没有分析任务" description="上传一张现场图片，开始第一条可追踪的安全闭环。" /></section>
      <section class="card"><div class="card-head"><div><p class="section-kicker">DUE SOON</p><h3>临近截止工单</h3></div><RouterLink class="button-icon" to="/work-orders">查看全部</RouterLink></div><div v-if="summary?.due_work_orders.length" class="compact-list"><RouterLink v-for="order in summary.due_work_orders" :key="order.id" :to="`/work-orders/${order.id}`" class="compact-item"><div><strong>{{ order.title }}</strong><small>{{ formatDateTime(order.deadline) }} · {{ statusLabel(order.status) }}</small></div><span>{{ riskLabel(order.risk_level) }}</span></RouterLink></div><AppState v-else title="暂无临近工单" description="确认一条整改草稿后，责任人与截止时间会出现在这里。" /></section>
      <section class="card chart-card span-2">
        <div class="card-head">
          <div><p class="section-kicker">ANOMALY SCAN</p><h3>异常波动检测</h3></div>
          <div class="module-toggle" aria-label="异常检测模块切换">
            <button type="button" :class="{ active: anomalyModule === 'safety' }" @click="switchAnomalyModule('safety')">安全</button>
            <button type="button" :class="{ active: anomalyModule === 'quality' }" @click="switchAnomalyModule('quality')">质量</button>
          </div>
        </div>
        <div v-if="anomalyLoading" class="loading-dots">正在检测异常波动</div>
        <template v-else-if="anomaly">
          <template v-if="anomaly.available">
            <div class="anomaly-hero">
              <strong>{{ anomaly.anomaly_days }}<small> / {{ anomaly.total_days }} 天</small></strong>
              <p class="muted-copy">{{ anomaly.anomaly_days ? `近 ${anomaly.total_days} 天检测到 ${anomaly.anomaly_days} 天异常波动，请核查对应日期的隐患记录。` : `近 ${anomaly.total_days} 天无异常波动，隐患计数保持平稳。` }}</p>
            </div>
            <div class="anomaly-bars" role="img" :aria-label="`近 ${anomaly.samples.length} 天${anomalyModule === 'safety' ? '安全' : '质量'}隐患按天计数`">
              <div v-for="sample in anomaly.samples.slice(-14)" :key="sample.date" class="anomaly-day" :title="`${sample.date} · ${sample.count} 条 · z=${sample.z}`">
                <span class="bar" :class="{ spike: sample.anomaly }" :style="{ height: anomalyBarHeight(sample.count) }"></span>
                <span class="day-label">{{ sample.date.slice(8).replace('-', '/') }}</span>
              </div>
            </div>
            <p class="helper-text">统计口径：按天隐患计数的 z-score，z &gt; 2.5 判定为异常日（红色标记）。</p>
          </template>
          <p v-else class="muted-copy">{{ anomaly.reason || '暂无异常检测数据' }}</p>
        </template>
        <p v-else class="muted-copy">暂无异常检测数据</p>
      </section>
    </div>
  </div>
</template>

<style scoped>
.module-toggle { display: inline-flex; gap: 4px; padding: 3px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface-soft); }
.module-toggle button { min-height: 44px; padding: 4px 12px; border: 0; border-radius: 6px; background: transparent; color: var(--muted); font-size: 11px; font-weight: 600; cursor: pointer; }
.module-toggle button.active { background: var(--surface); color: var(--text); box-shadow: var(--shadow-sm); }
.module-toggle { background: var(--surface-soft); }
.module-toggle button.active { background: var(--surface); color: var(--primary); box-shadow: var(--shadow-sm); }
.trend-line { stroke: var(--primary); }
.trend-glow { stroke: var(--cyan); }
.status-bars { display: grid; gap: 15px; padding-top: 4px; }
.status-bar-row > div:first-child { display: flex; align-items: center; justify-content: space-between; gap: 12px; color: var(--text-soft); font-size: 11px; }
.status-bar-row b { color: var(--text); font-variant-numeric: tabular-nums; }
.status-bar-track { height: 8px; overflow: hidden; margin-top: 7px; border-radius: 999px; background: var(--surface-muted); }
.status-bar-track span { display: block; height: 100%; border-radius: inherit; background: var(--primary); transition: width var(--ease); }
.anomaly-hero { display: flex; align-items: baseline; gap: 12px; margin-bottom: 12px; }
.anomaly-hero > strong { font-size: 26px; font-weight: 800; color: var(--text); font-variant-numeric: tabular-nums; }
.anomaly-hero > strong small { font-size: 12px; font-weight: 600; color: var(--muted); }
.anomaly-bars { display: flex; align-items: flex-end; gap: 6px; height: 120px; padding: 8px 4px 0; border-bottom: 1px solid var(--line); }
.anomaly-day { display: grid; grid-template-rows: 1fr 14px; gap: 4px; flex: 1; height: 100%; align-items: end; }
.anomaly-day .bar { display: block; width: 100%; min-height: 2px; border-radius: 3px 3px 0 0; background: var(--primary-soft); transition: height 0.2s ease; }
.anomaly-day .bar.spike { background: var(--danger); }
.anomaly-day .day-label { text-align: center; color: var(--muted); font-size: 9px; font-variant-numeric: tabular-nums; }
</style>
