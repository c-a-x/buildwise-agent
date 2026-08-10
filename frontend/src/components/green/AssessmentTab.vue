<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { getApiError } from '@/api/http'
import { greenApi } from '@/api/green'
import AdvicePanel from '@/components/green/AdvicePanel.vue'
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageHeader from '@/components/common/AppPageHeader.vue'
import { useGreenStore } from '@/stores/green'
import { useProjectStore } from '@/stores/project'
import { formatDateTime } from '@/utils/date'
import type { DimensionScore, GreenAssessmentResult } from '@/types/green'

type DimensionKey = 'material' | 'water' | 'energy' | 'land' | 'env'

interface MetricDef { key: string; name: string; target: string; hint: string }
interface DimensionDef { key: DimensionKey; name: string; metrics: MetricDef[] }

const dimensionConfig: DimensionDef[] = [
  {
    key: 'material', name: '节材',
    metrics: [
      { key: 'recycled_material_pct', name: '可循环材料利用率', target: '30%', hint: '越高越好' },
      { key: 'template_reuse_times', name: '模板周转次数', target: '6 次', hint: '越高越好' },
      { key: 'material_recycle_rate', name: '建筑垃圾回收利用率', target: '50%', hint: '越高越好' },
    ],
  },
  {
    key: 'water', name: '节水',
    metrics: [
      { key: 'non_traditional_water_pct', name: '非传统水源利用率', target: '30%', hint: '越高越好' },
      { key: 'water_saving_pct', name: '节水节水量占比', target: '15%', hint: '越高越好' },
    ],
  },
  {
    key: 'energy', name: '节能',
    metrics: [
      { key: 'energy_saving_pct', name: '节能设备节电率', target: '20%', hint: '越高越好' },
      { key: 'renewable_energy_pct', name: '可再生能源占比', target: '10%', hint: '越高越好' },
    ],
  },
  {
    key: 'land', name: '节地',
    metrics: [
      { key: 'land_saving_pct', name: '节约集约用地率', target: '20%', hint: '越高越好' },
      { key: 'greening_rate', name: '现场绿化率', target: '20%', hint: '越高越好' },
    ],
  },
  {
    key: 'env', name: '环境保护',
    metrics: [
      { key: 'env_compliance_pct', name: '环保措施落实率', target: '100%', hint: '越高越好' },
      { key: 'sewage_treatment_pct', name: '污水达标处理率', target: '100%', hint: '越高越好' },
    ],
  },
]

const projects = useProjectStore()
const green = useGreenStore()
const areaM2 = ref('')
const title = ref('')
const localError = ref('')
const inputs = reactive<Record<DimensionKey, Record<string, string>>>({
  material: { recycled_material_pct: '', template_reuse_times: '', material_recycle_rate: '' },
  water: { non_traditional_water_pct: '', water_saving_pct: '' },
  energy: { energy_saving_pct: '', renewable_energy_pct: '' },
  land: { land_saving_pct: '', greening_rate: '' },
  env: { env_compliance_pct: '', sewage_treatment_pct: '' },
})

const result = (): GreenAssessmentResult | null => green.currentAssessment

const levelClass = (level: string): string => {
  if (level === '优秀' || level === '优良') return 'success'
  if (level === '合格') return 'warning'
  return 'danger'
}

function numValue(raw: string): number | null {
  const value = Number(raw)
  return raw.trim() === '' || Number.isNaN(value) ? null : value
}

function fillSample(): void {
  areaM2.value = '8500'
  title.value = '主体结构阶段评估'
  inputs.material = { recycled_material_pct: '28', template_reuse_times: '6', material_recycle_rate: '45' }
  inputs.water = { non_traditional_water_pct: '27', water_saving_pct: '13' }
  inputs.energy = { energy_saving_pct: '18', renewable_energy_pct: '9' }
  inputs.land = { land_saving_pct: '17', greening_rate: '18' }
  inputs.env = { env_compliance_pct: '95', sewage_treatment_pct: '92' }
  localError.value = ''
}

function collectDimension(dimension: DimensionDef): { dimension: DimensionKey; metrics: Array<{ key: string; value: number | null }> } {
  return {
    dimension: dimension.key,
    metrics: dimension.metrics.map((metric) => ({ key: metric.key, value: numValue(inputs[dimension.key][metric.key] ?? '') })),
  }
}

async function submit(): Promise<void> {
  localError.value = ''
  if (!projects.currentProject?.id) { localError.value = '当前没有可用项目'; return }
  try {
    await green.submitAssessment({
      project_id: projects.currentProject.id,
      title: title.value,
      area_m2: numValue(areaM2.value),
      dimensions: dimensionConfig.map(collectDimension),
    })
  } catch (cause) { localError.value = getApiError(cause) }
}

async function viewAssessment(assessmentId: string): Promise<void> {
  localError.value = ''
  try {
    const detail = await greenApi.assessment(assessmentId)
    green.currentAssessment = detail
  } catch (cause) { localError.value = getApiError(cause) }
}

async function downloadReport(): Promise<void> {
  const current = result()
  if (!current) return
  localError.value = ''
  try {
    const blob = await greenApi.downloadAssessmentReport(current.assessment_id)
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `四节一环保评估报告_${current.assessment_id}.docx`
    anchor.click()
    URL.revokeObjectURL(url)
  } catch (cause) { localError.value = getApiError(cause) }
}

function fmt(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return String(value)
}

function barColor(score: number): string {
  if (score >= 85) return 'var(--success)'
  if (score >= 70) return 'var(--blue)'
  if (score >= 60) return 'var(--warning)'
  return 'var(--danger)'
}

onMounted(async () => {
  if (!projects.projects.length) await projects.loadProjects()
  await green.loadAssessments(projects.currentProject?.id)
})
</script>

<template>
  <div>
    <AppPageHeader eyebrow="GREEN ASSESSMENT" title="绿色建造 · 四节一环保评估" description="按节材、节水、节能、节地、环境保护五个维度量化评估项目绿色施工水平，生成等级与评估报告。">
      <template #actions><span class="status-pill dark"><span class="status-dot online" />四节一环保</span></template>
    </AppPageHeader>

    <div class="safety-layout">
      <section class="card input-panel">
        <div class="card-head"><div><p class="section-kicker">01 · INPUT</p><h3>录入五维指标</h3></div><span class="mono">每维 20% 权重</span></div>
        <div class="form-grid">
          <div class="form-field">
            <label>所属项目</label>
            <select :value="projects.currentProject?.id" @change="projects.selectProject(($event.target as HTMLSelectElement).value)">
              <option v-if="!projects.currentProject" value="">请选择项目</option>
              <option v-for="project in projects.projects" :key="project.id" :value="project.id">{{ project.name }}</option>
            </select>
          </div>
          <div class="two-fields">
            <div class="form-field">
              <label>建筑面积（m²）</label>
              <input v-model="areaM2" type="number" min="0" step="1" placeholder="如 8500" />
            </div>
            <div class="form-field">
              <label>评估主题</label>
              <input v-model="title" placeholder="如 主体结构阶段评估" />
            </div>
          </div>
          <button type="button" class="secondary-button button-block" @click="fillSample"><AppIcon name="leaf" :size="16" />填入示例数据</button>

          <div v-for="dimension in dimensionConfig" :key="dimension.key" class="item-section">
            <p class="section-kicker">{{ dimension.name }}</p>
            <div class="form-grid">
              <div v-for="metric in dimension.metrics" :key="metric.key" class="form-field">
                <label>{{ metric.name }}<span>{{ metric.target }}</span></label>
                <input v-model="inputs[dimension.key][metric.key]" type="number" min="0" step="any" :placeholder="metric.hint" />
              </div>
            </div>
          </div>

          <p v-if="localError" class="error-text">{{ localError }}</p>
          <button type="button" class="primary-button button-block" :disabled="green.submittingAssessment" @click="submit">
            <AppIcon name="leaf" :size="16" />{{ green.submittingAssessment ? '评估中…' : '开始四节一环保评估' }}
          </button>
          <p class="helper-text">缺失的指标按 0 分计并标记为演示结果，请尽量填写完整以获得准确等级。</p>
        </div>
      </section>

      <div class="result-column">
        <div v-if="!result()" class="card">
          <div class="placeholder-hero">
            <div class="placeholder-orbit"><AppIcon name="leaf" :size="30" /></div>
            <div><h2>暂无评估结果</h2><p>录入节材、节水、节能、节地、环境保护指标后点击「开始四节一环保评估」，这里会显示总分、等级与分维度得分。</p></div>
          </div>
        </div>

        <template v-else>
          <div class="result-hero assessment-hero">
            <div class="assessment-score">
              <p class="section-kicker">TOTAL SCORE</p>
              <strong class="score-number">{{ result()!.total_score }}</strong>
              <span class="status-pill" :class="levelClass(result()!.level)">{{ result()!.level }}</span>
              <p class="helper-text">总分 = 五维均分 × 20% 加权{{ result()!.is_simulated ? ' · 含未填写指标（演示）' : '' }}</p>
            </div>
            <div class="assessment-meta">
              <p><small>项目</small><strong>{{ result()!.project_name }}</strong></p>
              <p><small>建筑面积</small><strong>{{ fmt(result()!.area_m2) }} m²</strong></p>
              <p><small>评估编号</small><strong class="mono">{{ result()!.assessment_id }}</strong></p>
            </div>
          </div>

          <div class="dimension-grid">
            <div v-for="dimension in result()!.dimensions" :key="dimension.dimension" class="card dimension-card">
              <div class="dimension-head">
                <strong>{{ dimension.name }}</strong>
                <b :style="{ color: barColor(dimension.score) }">{{ fmt(dimension.score) }}</b>
              </div>
              <div class="score-track"><span :style="{ width: `${Math.min(dimension.score, 100)}%`, background: barColor(dimension.score) }" /></div>
              <div class="dimension-metrics">
                <p v-for="metric in dimension.metrics" :key="metric.key">
                  <span>{{ metric.name }}</span>
                  <b>{{ fmt(metric.score) }}</b>
                </p>
              </div>
            </div>
          </div>

          <div class="result-tools">
            <button type="button" class="secondary-button" @click="downloadReport"><AppIcon name="download" :size="16" />下载 Word 报告</button>
          </div>

          <AdvicePanel source-type="assessment" :assessment-id="result()!.assessment_id" />

          <section class="card">
            <div class="card-head"><div><p class="section-kicker">REPORT</p><h3>评估报告预览</h3></div><span class="mono">{{ formatDateTime(result()!.created_at) }}</span></div>
            <pre class="report-pre">{{ result()!.report_preview }}</pre>
          </section>
        </template>
      </div>
    </div>

    <section class="card history-card">
      <div class="card-head"><div><p class="section-kicker">HISTORY</p><h3>评估历史</h3></div><span class="mono">{{ green.assessments.length }} 条</span></div>
      <div v-if="green.loadingAssessments" class="table-wrap"><div class="loading-dots">正在加载历史</div></div>
      <div v-else-if="!green.assessments.length" class="table-wrap"><p class="muted-copy">暂无评估记录，完成一次评估后这里会显示历史清单。</p></div>
      <div v-else class="table-wrap">
        <table class="data-table">
          <thead><tr><th>评估编号</th><th>项目</th><th class="align-right">总分</th><th>等级</th><th>时间</th><th class="action-cell">操作</th></tr></thead>
          <tbody>
            <tr v-for="entry in green.assessments" :key="entry.assessment_id">
              <td><strong>{{ entry.assessment_id }}</strong><small>{{ entry.title || '—' }}</small></td>
              <td>{{ entry.project_name }}</td>
              <td class="align-right"><strong>{{ fmt(entry.total_score) }}</strong></td>
              <td><span class="status-pill" :class="levelClass(entry.level)">{{ entry.level }}</span></td>
              <td>{{ formatDateTime(entry.created_at) }}</td>
              <td class="action-cell"><button type="button" class="button-icon" @click="viewAssessment(entry.assessment_id)">查看</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.item-section { border-top: 1px solid var(--line); padding-top: 15px; }
.item-section:first-of-type { border-top: 0; padding-top: 0; }
.item-section .form-grid { gap: 10px; }
.assessment-hero { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(260px, 0.9fr); padding: 22px; border: 1px solid var(--line); border-radius: 12px; background: linear-gradient(145deg, #f7faff, #fbfdff); }
.assessment-score .score-number { display: block; margin: 4px 0 10px; font-size: 42px; font-weight: 800; line-height: 1; color: var(--text); font-variant-numeric: tabular-nums; }
.assessment-meta { display: grid; align-content: center; gap: 10px; border-left: 1px solid var(--line); padding-left: 20px; }
.assessment-meta p { margin: 0; display: flex; align-items: baseline; justify-content: space-between; gap: 10px; }
.assessment-meta small { color: var(--muted); font-size: 10px; }
.assessment-meta strong { font-size: 12px; color: var(--text); }
.dimension-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; margin-top: 14px; }
.dimension-card { padding: 14px; }
.dimension-head { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 8px; }
.dimension-head strong { font-size: 13px; color: var(--text); }
.dimension-head b { font-size: 18px; font-variant-numeric: tabular-nums; }
.score-track { height: 6px; overflow: hidden; border-radius: 6px; background: var(--surface-muted); }
.score-track span { display: block; height: 100%; border-radius: inherit; }
.dimension-metrics { display: grid; gap: 5px; margin-top: 10px; }
.dimension-metrics p { margin: 0; display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.dimension-metrics span { color: var(--muted); font-size: 10px; }
.dimension-metrics b { color: var(--text-soft); font-size: 11px; font-variant-numeric: tabular-nums; }
.result-tools { display: flex; justify-content: flex-end; margin-top: 14px; }
.report-pre { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; color: var(--text-soft); font-family: 'Fira Code', monospace; font-size: 11px; line-height: 1.8; }
.history-card { margin-top: 18px; }
.align-right { text-align: right; }
@media (max-width: 900px) { .assessment-hero { grid-template-columns: 1fr; } .assessment-meta { border-left: 0; border-top: 1px solid var(--line); padding-left: 0; padding-top: 14px; } }
</style>
