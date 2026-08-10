<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { getApiError } from '@/api/http'
import { greenApi } from '@/api/green'
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageHeader from '@/components/common/AppPageHeader.vue'
import { useGreenStore } from '@/stores/green'
import { useProjectStore } from '@/stores/project'
import { formatDateTime } from '@/utils/date'
import type { EnvRecord, EnvThreshold } from '@/types/green'

interface MetricDef { key: string; name: string; unit: string }
interface GroupDef { name: string; metrics: MetricDef[] }

const metricGroups: GroupDef[] = [
  { name: '扬尘', metrics: [
    { key: 'pm25', name: 'PM2.5', unit: 'μg/m³' },
    { key: 'pm10', name: 'PM10', unit: 'μg/m³' },
    { key: 'tsp', name: 'TSP', unit: 'μg/m³' },
  ] },
  { name: '噪声', metrics: [
    { key: 'noise_day_db', name: '昼间', unit: 'dB(A)' },
    { key: 'noise_night_db', name: '夜间', unit: 'dB(A)' },
  ] },
  { name: '污水', metrics: [
    { key: 'cod_mg', name: 'COD', unit: 'mg/L' },
    { key: 'ss_mg', name: 'SS', unit: 'mg/L' },
    { key: 'ph', name: 'pH', unit: '' },
  ] },
  { name: '固废', metrics: [
    { key: 'solid_waste_t', name: '建筑垃圾', unit: 't' },
  ] },
]

const allMetricKeys = metricGroups.flatMap((group) => group.metrics.map((metric) => metric.key))

const projects = useProjectStore()
const green = useGreenStore()
const recordDate = ref(new Date().toISOString().slice(0, 10))
const alertOnly = ref(false)
const localError = ref('')
const thresholdMap = ref<Record<string, EnvThreshold>>({})
const values = reactive<Record<string, string>>(Object.fromEntries(allMetricKeys.map((key) => [key, ''])))

const thresholdsLoaded = computed(() => Object.keys(thresholdMap.value).length > 0)

function thresholdHint(key: string): string {
  const threshold = thresholdMap.value[key]
  if (!threshold) return ''
  if (threshold.rule === 'above') return `限值 ${threshold.limit} ${threshold.unit}`
  return `范围 ${threshold.min}~${threshold.max}`
}

function numValue(raw: string): number | null {
  const value = Number(raw)
  return raw.trim() === '' || Number.isNaN(value) ? null : value
}

function fillSample(): void {
  values.pm25 = '120'
  values.pm10 = '90'
  values.tsp = '220'
  values.noise_day_db = '65'
  values.noise_night_db = '52'
  values.cod_mg = '55'
  values.ss_mg = '32'
  values.ph = '7.2'
  values.solid_waste_t = '2.2'
  localError.value = ''
}

async function save(): Promise<void> {
  localError.value = ''
  if (!projects.currentProject?.id) { localError.value = '当前没有可用项目'; return }
  if (!recordDate.value) { localError.value = '请选择记录日期'; return }
  try {
    const payload = { project_id: projects.currentProject.id, record_date: recordDate.value } as Record<string, string | number | null>
    for (const key of allMetricKeys) payload[key] = numValue(values[key] ?? '')
    const record = await green.saveEnvRecord(payload as unknown as Parameters<typeof green.saveEnvRecord>[0])
    localError.value = record.has_alerts ? '已保存，检测到超标指标，请在表格中查看告警。' : ''
    for (const key of allMetricKeys) values[key] = ''
  } catch (cause) { localError.value = getApiError(cause) }
}

function fmt(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return String(value)
}

async function applyFilter(): Promise<void> {
  await green.loadEnvRecords({ project_id: projects.currentProject?.id, alert_only: alertOnly.value })
}

function alertKeys(record: EnvRecord): string[] {
  return record.alerts.map((alert) => alert.key)
}

onMounted(async () => {
  if (!projects.projects.length) await projects.loadProjects()
  if (!green.envThresholds.length) {
    try {
      const thresholds = await greenApi.envThresholds()
      thresholdMap.value = Object.fromEntries(thresholds.map((threshold) => [threshold.key, threshold]))
    } catch (cause) { localError.value = getApiError(cause) }
  }
  await green.loadEnvRecords({ project_id: projects.currentProject?.id })
})
</script>

<template>
  <div>
    <AppPageHeader eyebrow="ENV LEDGER" title="绿色建造 · 环保监测台账" description="记录扬尘、噪声、污水与固废日常监测读数，超限指标自动标注告警，支持按日期与告警筛选。">
      <template #actions><span class="status-pill dark"><span class="status-dot online" />环保监测</span></template>
    </AppPageHeader>

    <div class="safety-layout">
      <section class="card input-panel">
        <div class="card-head"><div><p class="section-kicker">01 · RECORD</p><h3>录入当日监测读数</h3></div><span class="mono">{{ recordDate }}</span></div>
        <div class="form-grid">
          <div class="form-field">
            <label>所属项目</label>
            <select :value="projects.currentProject?.id" @change="projects.selectProject(($event.target as HTMLSelectElement).value)">
              <option v-if="!projects.currentProject" value="">请选择项目</option>
              <option v-for="project in projects.projects" :key="project.id" :value="project.id">{{ project.name }}</option>
            </select>
          </div>
          <div class="form-field">
            <label>记录日期<span>可重录当日</span></label>
            <input v-model="recordDate" type="date" />
          </div>

          <div v-for="group in metricGroups" :key="group.name" class="item-section">
            <p class="section-kicker">{{ group.name }}</p>
            <div class="form-grid">
              <div v-for="metric in group.metrics" :key="metric.key" class="form-field">
                <label>{{ metric.name }}（{{ metric.unit }}）<span>{{ thresholdHint(metric.key) }}</span></label>
                <input v-model="values[metric.key]" type="number" min="0" step="any" :placeholder="metric.unit" />
              </div>
            </div>
          </div>

          <button type="button" class="secondary-button button-block" @click="fillSample"><AppIcon name="leaf" :size="16" />填入示例数据</button>

          <p v-if="localError" class="error-text">{{ localError }}</p>
          <button type="button" class="primary-button button-block" :disabled="green.savingEnvRecord" @click="save">
            <AppIcon name="leaf" :size="16" />{{ green.savingEnvRecord ? '保存中…' : '保存当日记录' }}
          </button>
          <p v-if="green.envError" class="error-text">{{ green.envError }}</p>
          <p class="helper-text">同一天重复提交会覆盖原记录（幂等重录）。超标读数会立即在下方列表中标红提醒。</p>
        </div>
      </section>

      <div class="result-column">
        <section class="card">
          <div class="card-head">
            <div><p class="section-kicker">LEDGER</p><h3>监测台账</h3></div>
            <div class="filter-row">
              <label class="checkbox-line"><input v-model="alertOnly" type="checkbox" @change="applyFilter" /><span>仅看超标</span></label>
              <span class="mono">{{ green.envRecords.length }} 条</span>
            </div>
          </div>
          <div v-if="green.loadingEnvRecords" class="table-wrap"><div class="loading-dots">正在加载台账</div></div>
          <div v-else-if="!green.envRecords.length" class="table-wrap"><p class="muted-copy">暂无监测记录，录入当日读数后这里会显示台账。</p></div>
          <div v-else class="table-wrap">
            <table class="data-table">
              <thead>
                <tr><th>日期</th><th>PM2.5</th><th>PM10</th><th>TSP</th><th>昼噪</th><th>夜噪</th><th>COD</th><th>SS</th><th>pH</th><th>固废(t)</th><th>状态</th></tr>
              </thead>
              <tbody>
                <tr v-for="record in green.envRecords" :key="record.record_id" :class="{ 'alert-row': record.has_alerts }">
                  <td><strong>{{ record.record_date }}</strong><small>{{ record.project_name }}</small></td>
                  <td :class="alertKeys(record).includes('pm25') ? 'alert-cell' : ''">{{ fmt(record.pm25) }}</td>
                  <td :class="alertKeys(record).includes('pm10') ? 'alert-cell' : ''">{{ fmt(record.pm10) }}</td>
                  <td :class="alertKeys(record).includes('tsp') ? 'alert-cell' : ''">{{ fmt(record.tsp) }}</td>
                  <td :class="alertKeys(record).includes('noise_day_db') ? 'alert-cell' : ''">{{ fmt(record.noise_day_db) }}</td>
                  <td :class="alertKeys(record).includes('noise_night_db') ? 'alert-cell' : ''">{{ fmt(record.noise_night_db) }}</td>
                  <td :class="alertKeys(record).includes('cod_mg') ? 'alert-cell' : ''">{{ fmt(record.cod_mg) }}</td>
                  <td :class="alertKeys(record).includes('ss_mg') ? 'alert-cell' : ''">{{ fmt(record.ss_mg) }}</td>
                  <td :class="alertKeys(record).includes('ph') ? 'alert-cell' : ''">{{ fmt(record.ph) }}</td>
                  <td>{{ fmt(record.solid_waste_t) }}</td>
                  <td>
                    <span v-if="record.has_alerts" class="status-pill danger"><span class="status-dot online" />超标</span>
                    <span v-else class="status-pill success"><span class="status-dot online" />正常</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-if="!green.envError" class="helper-text">记录时间：{{ green.envRecords[0] ? formatDateTime(green.envRecords[0].created_at) : '—' }}</p>
        </section>

        <section class="card">
          <div class="card-head"><div><p class="section-kicker">THRESHOLDS</p><h3>控制限值</h3></div><span class="mono">GB 12523 等</span></div>
          <div v-if="!thresholdsLoaded" class="loading-dots">正在加载限值</div>
          <div v-else class="threshold-grid">
            <div v-for="threshold in Object.values(thresholdMap)" :key="threshold.key" class="threshold-item">
              <p>{{ threshold.name }}<small>{{ threshold.unit }}</small></p>
              <b>{{ threshold.rule === 'above' ? `≤ ${threshold.limit}` : `${threshold.min} ~ ${threshold.max}` }}</b>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.item-section { border-top: 1px solid var(--line); padding-top: 15px; }
.item-section:first-of-type { border-top: 0; padding-top: 0; }
.item-section .form-grid { gap: 10px; }
.filter-row { display: flex; align-items: center; gap: 12px; }
.alert-row { background: var(--danger-bg); }
.alert-cell { color: var(--danger); font-weight: 800; }
.threshold-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }
.threshold-item { border: 1px solid var(--line); border-radius: 9px; padding: 11px 13px; background: var(--surface-soft); }
.threshold-item p { margin: 0 0 4px; color: var(--muted); font-size: 10px; }
.threshold-item p small { margin-left: 4px; }
.threshold-item b { font-size: 13px; color: var(--text); font-variant-numeric: tabular-nums; }
</style>
