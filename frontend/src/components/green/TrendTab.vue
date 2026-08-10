<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { getApiError } from '@/api/http'
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageHeader from '@/components/common/AppPageHeader.vue'
import AppState from '@/components/common/AppState.vue'
import { useGreenStore } from '@/stores/green'
import { useProjectStore } from '@/stores/project'
import type { GreenTrendPoint } from '@/types/green'

const projects = useProjectStore()
const green = useGreenStore()
const targetInput = ref('')
const noteInput = ref('')
const localError = ref('')

const points = computed<GreenTrendPoint[]>(() => green.trend?.points ?? [])
const current = computed(() => green.trend?.current)

const chartWidth = 650
const chartHeight = 190
const padTop = 12

const yMax = computed<number>(() => {
  const intensities = points.value.map((point) => point.intensity)
  const target = green.target?.target_intensity
  if (target) intensities.push(target)
  const max = intensities.length ? Math.max(...intensities) : 1
  return max * 1.15 || 1
})

function yFor(value: number): number {
  return chartHeight - (value / yMax.value) * chartHeight + padTop
}

const trendPoints = computed<string>(() => {
  if (points.value.length <= 1) return ''
  const step = chartWidth / (points.value.length - 1)
  return points.value.map((point, index) => `${(index * step).toFixed(1)},${yFor(point.intensity).toFixed(1)}`).join(' ')
})

const xLabels = computed<Array<{ label: string; x: number }>>(() => {
  if (points.value.length <= 1) return []
  const step = chartWidth / (points.value.length - 1)
  return points.value.map((point, index) => ({ label: point.created_at.slice(0, 10), x: index * step }))
})

const targetLineY = computed<number | null>(() => {
  const target = green.target?.target_intensity
  return target == null ? null : yFor(target)
})

const gradeClass = computed<string>(() => {
  switch (current.value?.grade) {
    case '达标': return 'success'
    case '临界': return 'warning'
    case '超标': return 'danger'
    default: return 'muted'
  }
})

function fmt(value: number | null | undefined, digits = 4): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return value.toFixed(digits)
}

async function refresh(): Promise<void> {
  const projectId = projects.currentProject?.id
  if (!projectId) return
  await green.loadTrend(projectId)
  await green.loadTarget(projectId)
}

function onProjectChange(): void {
  localError.value = ''
  targetInput.value = ''
  noteInput.value = ''
  void refresh()
}

function fillSample(): void {
  targetInput.value = '0.08'
  noteInput.value = '对标行业先进水平（0.08 tCO2e/m²）'
  localError.value = ''
}

async function saveTarget(): Promise<void> {
  localError.value = ''
  if (!projects.currentProject?.id) { localError.value = '当前没有可用项目'; return }
  const value = targetInput.value.trim() === '' ? null : Number(targetInput.value)
  if (targetInput.value.trim() !== '' && (Number.isNaN(value) || value! <= 0)) { localError.value = '目标强度需为正数'; return }
  try {
    await green.saveTarget({ project_id: projects.currentProject.id, target_intensity: value, note: noteInput.value })
    await green.loadTrend(projects.currentProject.id)
  } catch (cause) { localError.value = getApiError(cause) }
}

watch(() => projects.currentProject?.id, () => onProjectChange())

onMounted(async () => {
  if (!projects.projects.length) await projects.loadProjects()
  await refresh()
})
</script>

<template>
  <div>
    <AppPageHeader eyebrow="CARBON TREND" title="绿色建造 · 碳排趋势与目标" description="查看项目历次碳排核算的面积强度曲线，设定强度目标并跟踪达标、临界与超标状态。">
      <template #actions><span class="status-pill dark"><span class="status-dot online" />强度 tCO2e/m²</span></template>
    </AppPageHeader>

    <div class="safety-layout">
      <section class="card input-panel">
        <div class="card-head"><div><p class="section-kicker">TARGET</p><h3>设定强度目标</h3></div><span class="mono">tCO2e/m²</span></div>
        <div class="form-grid">
          <div class="form-field">
            <label>所属项目</label>
            <select :value="projects.currentProject?.id" @change="onProjectChange">
              <option v-if="!projects.currentProject" value="">请选择项目</option>
              <option v-for="project in projects.projects" :key="project.id" :value="project.id">{{ project.name }}</option>
            </select>
          </div>
          <div class="form-field">
            <label>目标强度（tCO2e/m²）<span>{{ green.target?.target_intensity != null ? `当前 ${green.target.target_intensity}` : '未设置' }}</span></label>
            <input v-model="targetInput" type="number" min="0" step="0.001" :placeholder="green.target?.target_intensity != null ? String(green.target.target_intensity) : '如 0.15'" />
          </div>
          <div class="form-field">
            <label>目标备注</label>
            <input v-model="noteInput" :placeholder="green.target?.note || '如 对标先进水平'" />
          </div>
          <p v-if="localError" class="error-text">{{ localError }}</p>
          <button type="button" class="secondary-button button-block" @click="fillSample"><AppIcon name="leaf" :size="16" />填入示例目标</button>
          <button type="button" class="primary-button button-block" :disabled="green.savingTarget" @click="saveTarget">
            <AppIcon name="settings" :size="16" />{{ green.savingTarget ? '保存中…' : '保存目标强度' }}
          </button>
          <p class="helper-text">达标 = 强度 ≤ 目标；临界 = ≤ 目标的 1.1 倍；其余为超标。目标保存后曲线会绘制参考线。</p>
        </div>
      </section>

      <div class="result-column">
        <section class="card chart-card">
          <div class="card-head"><div><p class="section-kicker">INTENSITY TREND</p><h3>面积强度曲线</h3></div><span class="mono">{{ points.length }} 次核算</span></div>
          <div v-if="green.loadingTrend" class="loading-dots">正在加载趋势</div>
          <AppState v-else-if="!points.length" type="empty" title="暂无碳排核算" description="先在「碳排核算」标签页完成至少一次核算，这里会绘制强度曲线。" />
          <template v-else>
            <div class="line-chart">
              <svg :viewBox="`0 0 ${chartWidth} ${chartHeight + padTop}`" role="img" aria-label="碳排面积强度趋势曲线">
                <line v-if="targetLineY !== null" class="trend-target" :x1="0" :y1="targetLineY" :x2="chartWidth" :y2="targetLineY" />
                <polyline class="trend-line" :points="trendPoints" fill="none" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
                <polyline class="trend-glow" :points="trendPoints" fill="none" stroke-width="9" stroke-linecap="round" stroke-linejoin="round" opacity=".12" />
                <circle v-for="(point, index) in points" :key="index" :cx="xLabels[index]?.x ?? 0" :cy="yFor(point.intensity)" r="3.5" class="trend-dot" />
              </svg>
              <div class="x-labels"><span v-for="item in xLabels" :key="item.label" :style="{ left: `${(item.x / chartWidth) * 100}%` }">{{ item.label.slice(5) }}</span></div>
            </div>
            <div class="trend-legend">
              <span><i class="legend-line" />面积强度</span>
              <span v-if="targetLineY !== null"><i class="legend-target" />目标 {{ fmt(green.target?.target_intensity) }}</span>
            </div>
          </template>
        </section>

        <div v-if="current" class="metrics-grid result-tiles">
          <div class="metric-card">
            <div class="metric-top"><AppIcon class="metric-icon" name="spark" :size="18" /></div>
            <strong>{{ fmt(current.intensity) }}</strong>
            <p>最新面积强度（tCO2e/m²）</p>
          </div>
          <div class="metric-card">
            <div class="metric-top"><AppIcon class="metric-icon" name="settings" :size="18" /></div>
            <strong>{{ fmt(current.target_intensity) }}</strong>
            <p>目标强度（tCO2e/m²）</p>
          </div>
          <div class="metric-card">
            <div class="metric-top"><AppIcon class="metric-icon warning" name="book" :size="18" /></div>
            <strong><span class="status-pill" :class="gradeClass">{{ current.grade }}</span></strong>
            <p>当前状态<template v-if="current.gap_pct != null"> · 超目标 {{ current.gap_pct }}%</template></p>
          </div>
        </div>

        <section class="card">
          <div class="card-head"><div><p class="section-kicker">POINTS</p><h3>核算明细</h3></div><span class="mono">{{ points.length }} 条</span></div>
          <div class="table-wrap">
            <table class="data-table">
              <thead><tr><th>时间</th><th class="align-right">总排放（tCO2e）</th><th class="align-right">面积（m²）</th><th class="align-right">强度（tCO2e/m²）</th></tr></thead>
              <tbody>
                <tr v-for="point in points" :key="point.created_at">
                  <td>{{ point.created_at.slice(0, 10) }}</td>
                  <td class="align-right">{{ fmt(point.total_emission) }}</td>
                  <td class="align-right">{{ fmt(point.area_m2, 0) }}</td>
                  <td class="align-right"><strong>{{ fmt(point.intensity) }}</strong></td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.line-chart { position: relative; }
.line-chart svg { display: block; width: 100%; }
.x-labels { display: flex; justify-content: space-between; margin-top: 6px; }
.x-labels span { position: relative; color: var(--muted); font-size: 10px; transform: translateX(-50%); white-space: nowrap; }
.x-labels span:first-child { transform: none; }
.x-labels span:last-child { transform: translateX(-100%); }
.trend-line { stroke: var(--blue); }
.trend-glow { stroke: var(--blue); }
.trend-dot { fill: var(--blue); }
.trend-target { stroke: var(--warning); stroke-width: 1.5; stroke-dasharray: 5 4; }
.trend-legend { display: flex; gap: 14px; margin-top: 10px; color: var(--muted); font-size: 10px; }
.trend-legend span { display: inline-flex; align-items: center; gap: 5px; }
.legend-line { width: 16px; height: 3px; background: var(--blue); border-radius: 2px; }
.legend-target { width: 16px; height: 0; border-top: 2px dashed var(--warning); }
.result-tiles { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.align-right { text-align: right; }
@media (max-width: 640px) { .result-tiles { grid-template-columns: 1fr; } }
</style>
