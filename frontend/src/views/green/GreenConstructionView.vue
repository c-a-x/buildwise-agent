<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'

import { getApiError } from '@/api/http'
import { greenApi } from '@/api/green'
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageHeader from '@/components/common/AppPageHeader.vue'
import AppState from '@/components/common/AppState.vue'
import CarbonRing from '@/components/green/CarbonRing.vue'
import { useGreenStore } from '@/stores/green'
import { useProjectStore } from '@/stores/project'
import { formatDateTime } from '@/utils/date'
import type { CarbonAnalysisResult, GreenBenchmark, GreenFactor, GreenItemInput, GreenReference } from '@/types/green'

type Category = 'material' | 'energy' | 'transport'
interface ItemRow { code: string; name: string; quantity: number; unit: string }

const projects = useProjectStore()
const green = useGreenStore()
const areaM2 = ref('')
const scope = ref('')
const localError = ref('')
const rows = reactive<Record<Category, ItemRow[]>>({ material: [], energy: [], transport: [] })
const result = computed<CarbonAnalysisResult | null>(() => green.currentResult)
const benchmark = ref<GreenBenchmark | null>(null)
const benchmarkLoading = ref(false)
const reference = ref<GreenReference | null>(null)
const referenceLoading = ref(false)
const referenceError = ref('')

watch(
  [result, () => projects.currentProject?.id],
  async () => {
    const projectId = projects.currentProject?.id
    if (!result.value || result.value.intensity == null || !projectId) {
      benchmark.value = null
      return
    }
    benchmarkLoading.value = true
    try {
      benchmark.value = await greenApi.benchmark(projectId)
    } catch {
      benchmark.value = null
    } finally {
      benchmarkLoading.value = false
    }
  },
  { immediate: true },
)

const categories: Array<{ key: Category; label: string; kicker: string; stageName: string }> = [
  { key: 'material', label: '材料清单', kicker: 'A1-A3', stageName: '建材生产' },
  { key: 'transport', label: '运输记录', kicker: 'A4', stageName: '建材运输' },
  { key: 'energy', label: '施工能耗', kicker: 'A5', stageName: '施工过程' },
]

const modePill = computed(() => {
  if (!result.value) return '离线因子核算'
  return result.value.is_simulated ? '演示因子核算' : '核证因子核算'
})

function factorOptions(category: Category): GreenFactor[] {
  return green.factors.filter((factor) => factor.category === category)
}

function addRow(category: Category): void {
  rows[category].push({ code: '', name: '', quantity: 1, unit: '' })
}

function removeRow(category: Category, index: number): void {
  rows[category].splice(index, 1)
}

function onFactorChange(category: Category, index: number, event: Event): void {
  const code = (event.target as HTMLSelectElement).value
  const factor = green.factors.find((item) => item.code === code)
  const row = rows[category][index]
  if (!row) return
  row.code = code
  row.name = factor?.name ?? ''
  row.unit = factor?.unit ?? ''
}

function rowHasCode(category: Category, row: ItemRow): boolean {
  return Boolean(row.code) && !factorOptions(category).some((factor) => factor.code === row.code)
}

function selectProject(event: Event): void {
  projects.selectProject((event.target as HTMLSelectElement).value)
  void green.loadAnalyses(projects.currentProject?.id)
}

function fillSample(): void {
  rows.material = [
    { code: 'CONCRETE_C30', name: 'C30商品混凝土', quantity: 860, unit: 'm3' },
    { code: 'REBAR_HOT_ROLLED', name: '热轧钢筋', quantity: 120, unit: 't' },
  ]
  rows.transport = [{ code: 'TRUCK_46T_DIESEL', name: '重型柴油货车(46t)', quantity: 51600, unit: 't·km' }]
  rows.energy = [{ code: 'GRID_ELEC', name: '外购电力', quantity: 180000, unit: 'kWh' }]
  areaM2.value = '8500'
  scope.value = '一期主体结构施工阶段'
  localError.value = ''
}

function collect(category: Category): GreenItemInput[] {
  return rows[category]
    .filter((row) => row.quantity > 0)
    .map((row) => ({ code: row.code, name: row.name, quantity: row.quantity, unit: row.unit, note: '' }))
}

async function analyze(): Promise<void> {
  localError.value = ''
  if (!projects.currentProject?.id) { localError.value = '当前没有可用项目'; return }
  const hasAnyRow = categories.some((category) => rows[category.key].some((row) => row.quantity > 0))
  if (!hasAnyRow) { localError.value = '请至少填写一条材料、运输或能耗记录'; return }
  const area = areaM2.value.trim() === '' ? null : Number(areaM2.value)
  try {
    await green.analyze({
      project_id: projects.currentProject.id,
      area_m2: area,
      scope: scope.value,
      materials: collect('material'),
      transport: collect('transport'),
      energy: collect('energy'),
    })
    await green.loadAnalyses(projects.currentProject.id)
  } catch (cause) { localError.value = getApiError(cause) }
}

async function viewAnalysis(analysisId: string): Promise<void> {
  localError.value = ''
  try { await green.loadAnalysis(analysisId) } catch (cause) { localError.value = getApiError(cause) }
}

async function downloadReport(): Promise<void> {
  if (!result.value) return
  localError.value = ''
  try {
    const blob = await greenApi.downloadReport(result.value.analysis_id)
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `碳排核算报告_${result.value.analysis_id}.docx`
    anchor.click()
    URL.revokeObjectURL(url)
  } catch (cause) { localError.value = getApiError(cause) }
}

function fmt(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return value.toFixed(digits)
}

function fmtZ(z: number): string { return `z=${z >= 0 ? '+' : ''}${z.toFixed(2)}` }

function pct(share: number): string { return `${Math.round(share * 100)}%` }

async function loadReference(): Promise<void> {
  referenceLoading.value = true
  referenceError.value = ''
  try {
    reference.value = await greenApi.reference()
  } catch (cause) { referenceError.value = getApiError(cause) }
  finally { referenceLoading.value = false }
}

onMounted(async () => {
  if (!projects.projects.length) await projects.loadProjects()
  await green.loadFactors()
  await green.loadAnalyses(projects.currentProject?.id)
  await loadReference()
})
</script>

<template>
  <div>
    <AppPageHeader eyebrow="GREEN CONSTRUCTION" title="绿色建造 · 碳排核算" description="按 GB/T 51366-2019 因子法（排放 = 活动数据 × 排放因子）核算施工阶段 A1-A3 / A4 / A5 分阶段碳排放。">
      <template #actions><span class="status-pill dark"><span class="status-dot online" />{{ modePill }}</span></template>
    </AppPageHeader>

    <div class="safety-layout">
      <section class="card input-panel">
        <div class="card-head"><div><p class="section-kicker">01 · INPUT</p><h3>输入活动数据</h3></div><span class="mono">GB/T 51366-2019</span></div>
        <div class="form-grid">
          <div class="form-field">
            <label>所属项目</label>
            <select :value="projects.currentProject?.id" @change="selectProject">
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
              <label>核算范围备注</label>
              <input v-model="scope" placeholder="如 一期主体结构施工阶段" />
            </div>
          </div>
          <button type="button" class="secondary-button button-block" @click="fillSample"><AppIcon name="leaf" :size="16" />填入示例清单</button>

          <div v-for="category in categories" :key="category.key" class="item-section">
            <p class="section-kicker">{{ category.kicker }} · {{ category.stageName }}</p>
            <p class="item-label">{{ category.label }}</p>
            <div class="item-rows">
              <div v-for="(row, index) in rows[category.key]" :key="index" class="item-row">
                <select :value="row.code" @change="onFactorChange(category.key, index, $event)">
                  <option value="">选择排放因子…</option>
                  <option v-if="rowHasCode(category.key, row)" :value="row.code">{{ row.name }}</option>
                  <option v-for="factor in factorOptions(category.key)" :key="factor.code" :value="factor.code">{{ factor.name }}（{{ factor.factor }} {{ factor.factor_unit }}）{{ factor.verified ? '' : '· 待核证' }}</option>
                </select>
                <input v-model.number="row.quantity" type="number" min="0" step="0.01" placeholder="数量" />
                <span class="row-unit">{{ row.unit }}</span>
                <button type="button" class="remove-row" :aria-label="`删除${category.label}条目`" @click="removeRow(category.key, index)"><AppIcon name="close" :size="15" /></button>
              </div>
            </div>
            <button type="button" class="button-icon" @click="addRow(category.key)"><AppIcon name="plus" :size="14" />添加一条{{ category.label.replace('清单', '') }}</button>
          </div>

          <p v-if="localError" class="error-text">{{ localError }}</p>
          <button type="button" class="primary-button button-block" :disabled="green.analyzing" @click="analyze">
            <AppIcon name="leaf" :size="16" />{{ green.analyzing ? '核算中…' : '开始碳排核算' }}
          </button>
          <p class="helper-text">演示因子（待核证）会在结果中明确标注；正式核算请先在因子库中替换为经核证的排放因子。</p>
        </div>
      </section>

      <div class="result-column">
        <div v-if="!result" class="card">
          <AppState type="empty" title="暂无核算结果" description="填写材料、运输与能耗清单后点击“开始碳排核算”，这里会显示分阶段排放与减排建议。" />
        </div>

        <template v-else>
          <CarbonRing :stages="result.stages" :total="result.total_emission" :unit="result.unit" />

          <div class="metrics-grid result-tiles">
            <div class="metric-card"><div class="metric-top"><AppIcon class="metric-icon" name="spark" :size="18" /></div><strong>{{ fmt(result.intensity) }}</strong><p>面积强度（tCO2e/m²）</p></div>
            <div class="metric-card"><div class="metric-top"><AppIcon class="metric-icon warning" name="book" :size="18" /></div><strong>3</strong><p>核算阶段 A1-A3 / A4 / A5</p></div>
            <div class="metric-card"><div class="metric-top"><AppIcon class="metric-icon" name="settings" :size="18" /></div><strong class="factor-version">{{ result.factor_version || '—' }}</strong><p>因子库版本</p></div>
          </div>

          <section class="card benchmark-card">
            <div class="card-head"><div><p class="section-kicker">BENCHMARK</p><h3>同类项目对标</h3></div><span v-if="benchmark" class="mono">{{ benchmark.available ? `${benchmark.count} 个项目 · z-score` : '样本不足' }}</span></div>
            <div v-if="benchmarkLoading" class="loading-dots">正在加载对标数据</div>
            <template v-else-if="benchmark?.available">
              <div v-if="benchmark.current" class="benchmark-hero">
                <strong>{{ benchmark.current.rank }}<small> / {{ benchmark.count }}</small></strong>
                <div class="benchmark-hero-copy">
                  <p class="benchmark-hero-title">本项目按面积强度排名第 {{ benchmark.current.rank }} 名</p>
                  <p class="benchmark-hero-meta">优于 {{ Math.round(benchmark.current.better_than_pct) }}% 的同类项目 · {{ fmtZ(benchmark.current.z) }}</p>
                </div>
              </div>
              <p v-else class="muted-copy">当前核算未命中对标项目，以下为全部项目强度榜单。</p>
              <div class="benchmark-list">
                <div v-for="item in benchmark.items.slice(0, 5)" :key="item.project_id" class="benchmark-row" :class="{ self: benchmark.current?.project_id === item.project_id }">
                  <span class="rank mono">{{ item.rank }}</span>
                  <span class="name">{{ item.project_name }}</span>
                  <span class="intensity mono">{{ fmt(item.intensity, 3) }}</span>
                  <span class="z mono" :class="item.z < 0 ? 'good' : 'bad'">{{ fmtZ(item.z) }}</span>
                </div>
              </div>
              <p class="helper-text">统计口径：每项目取最新一条有建筑面积的核算，面积强度（tCO2e/m²）z-score 越负代表碳排放越优。</p>
            </template>
            <p v-else class="muted-copy">{{ benchmark?.reason || '暂无足够样本进行对标' }}</p>
          </section>

          <div class="result-tools">
            <button type="button" class="secondary-button" @click="downloadReport"><AppIcon name="download" :size="16" />下载 Word 报告</button>
          </div>

          <div v-if="result.factor_warnings.length || result.has_unverified_factors" class="mode-note">
            <strong>核证提示</strong>
            <span v-if="result.has_unverified_factors">结果使用了未核证的演示排放因子，仅供演示；正式核算需替换为经核证的因子数据。</span>
            <span v-for="(warning, index) in result.factor_warnings" :key="index">{{ warning }}</span>
          </div>

          <section class="card">
            <div class="card-head"><div><p class="section-kicker">TOP CONTRIBUTORS</p><h3>主要贡献项</h3></div><span class="mono">Top 5</span></div>
            <div class="table-wrap">
              <table class="data-table">
                <thead><tr><th>项目</th><th>阶段</th><th class="align-right">排放（tCO2e）</th><th class="align-right">占比</th></tr></thead>
                <tbody>
                  <tr v-for="item in result.items.filter((entry) => !entry.factor_missing)" :key="`${item.stage}-${item.code}-${item.quantity}`">
                    <td><strong>{{ item.name }}</strong><small>{{ item.factor_source || '—' }}</small></td>
                    <td><span class="status-pill">{{ item.stage }} {{ item.stage_name }}</span></td>
                    <td class="align-right"><strong>{{ fmt(item.emission) }}</strong></td>
                    <td class="align-right">{{ result.total_emission ? pct(item.emission / result.total_emission) : '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section class="card">
            <div class="card-head"><div><p class="section-kicker">SUGGESTIONS</p><h3>减排建议</h3></div><span class="mono">绿色施工管理措施</span></div>
            <ul class="clean-list">
              <li v-for="(suggestion, index) in result.suggestions" :key="index"><AppIcon name="check" :size="15" /><span>{{ suggestion }}</span></li>
            </ul>
          </section>

          <section class="card">
            <div class="card-head"><div><p class="section-kicker">REPORT</p><h3>报告预览</h3></div><span class="mono">{{ formatDateTime(result.created_at) }}</span></div>
            <pre class="report-pre">{{ result.report_preview }}</pre>
          </section>
        </template>
      </div>
    </div>

    <section class="card reference-card">
      <div class="card-head">
        <div><p class="section-kicker">REAL-WORLD REFERENCE</p><h3>真实公开数据参考 · 中国建筑</h3></div>
        <span v-if="reference" class="status-pill success"><span class="status-dot online" />真实披露 · v{{ reference.version }}</span>
      </div>
      <p v-if="referenceError" class="error-text">{{ referenceError }}</p>
      <div v-else-if="referenceLoading" class="loading-dots">正在加载公开披露数据</div>
      <template v-else-if="reference">
        <p class="reference-note">{{ reference.source_note }}</p>
        <div class="reference-groups">
          <div v-for="group in reference.groups" :key="group.category" class="reference-group">
            <p class="reference-group-title">{{ group.name }}</p>
            <div class="reference-items">
              <div v-for="item in group.items" :key="item.code" class="reference-item">
                <p class="reference-item-name">{{ item.name }}</p>
                <p class="reference-item-value"><strong>{{ item.value }}</strong> <span v-if="item.unit" class="reference-item-unit">{{ item.unit }}</span></p>
                <p v-if="item.note" class="reference-item-note">{{ item.note }}</p>
                <p class="reference-item-source mono">{{ item.source }}<template v-if="item.year"> · {{ item.year }}</template></p>
              </div>
            </div>
          </div>
        </div>
        <p class="helper-text">数据来源为中国建筑公开报告，供真实对标参考，不参与本项目 z-score 排名。</p>
      </template>
      <p v-else class="muted-copy">暂无公开参考数据。</p>
    </section>

    <section class="card history-card">
      <div class="card-head"><div><p class="section-kicker">HISTORY</p><h3>核算历史</h3></div><span class="mono">{{ green.analyses.length }} 条</span></div>
      <div v-if="green.loadingList" class="table-wrap"><div class="loading-dots">正在加载历史</div></div>
      <div v-else-if="!green.analyses.length" class="table-wrap"><p class="muted-copy">暂无核算记录，完成一次分析后这里会显示历史清单。</p></div>
      <div v-else class="table-wrap">
        <table class="data-table">
          <thead><tr><th>分析编号</th><th>项目</th><th class="align-right">总排放（tCO2e）</th><th>模式</th><th>时间</th><th class="action-cell">操作</th></tr></thead>
          <tbody>
            <tr v-for="entry in green.analyses" :key="entry.analysis_id">
              <td><strong>{{ entry.analysis_id }}</strong><small>{{ entry.scope || '—' }}</small></td>
              <td>{{ entry.project_name }}</td>
              <td class="align-right"><strong>{{ fmt(entry.total_emission) }}</strong></td>
              <td><span class="status-pill" :class="entry.is_simulated ? 'warning' : 'success'">{{ entry.is_simulated ? '演示因子' : '核证因子' }}</span></td>
              <td>{{ formatDateTime(entry.created_at) }}</td>
              <td class="action-cell"><button type="button" class="button-icon" @click="viewAnalysis(entry.analysis_id)">查看</button></td>
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
.item-label { margin-bottom: 8px; color: var(--text-soft); font-size: 12px; font-weight: 700; }
.item-rows { display: grid; gap: 8px; }
.item-row { display: grid; grid-template-columns: minmax(0, 1fr) 78px 40px 34px; gap: 8px; align-items: center; }
.item-row select { min-height: 44px; padding: 0 42px 0 12px; font-size: 11px; }
.item-row input { min-height: 44px; padding: 0 12px; font-size: 11px; }
.row-unit { color: var(--muted); font-size: 10px; text-align: center; }
.remove-row { display: grid; width: 44px; height: 44px; place-items: center; border: 1px solid var(--line); border-radius: 8px; color: var(--danger); background: var(--surface); }
.remove-row:hover { border-color: var(--danger); background: var(--danger-bg); }
.result-tiles { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.benchmark-card { margin-top: 12px; }
.benchmark-hero { display: flex; align-items: center; gap: 14px; padding: 14px 16px; border-radius: 10px; background: var(--success-bg); border: 1px solid var(--success); }
.benchmark-hero > strong { font-size: 30px; font-weight: 800; color: var(--success); font-variant-numeric: tabular-nums; }
.benchmark-hero > strong small { font-size: 13px; font-weight: 600; color: var(--muted); }
.benchmark-hero-copy { display: grid; gap: 3px; }
.benchmark-hero-title { margin: 0; font-size: 13px; font-weight: 700; color: var(--text); }
.benchmark-hero-meta { margin: 0; font-size: 11px; color: var(--muted); }
.benchmark-list { display: grid; gap: 6px; margin-top: 12px; }
.benchmark-row { display: grid; grid-template-columns: 28px minmax(0, 1fr) 74px 74px; gap: 8px; align-items: center; padding: 8px 10px; border-radius: 8px; background: var(--surface-soft); }
.benchmark-row.self { outline: 1px solid var(--success); }
.benchmark-row .rank { color: var(--muted); }
.benchmark-row .name { font-size: 12px; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.benchmark-row .intensity { text-align: right; color: var(--text-soft); font-size: 11px; }
.benchmark-row .z { text-align: right; font-size: 11px; }
.benchmark-row .z.good { color: var(--success); }
.benchmark-row .z.bad { color: var(--danger); }
.result-tools { display: flex; justify-content: flex-end; margin-top: 2px; }
.result-tools .secondary-button { display: inline-flex; align-items: center; gap: 6px; }
.factor-version { font-family: 'Fira Code', monospace; font-size: 14px !important; }
.report-pre { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; color: var(--text-soft); font-family: 'Fira Code', monospace; font-size: 11px; line-height: 1.8; }
.history-card { margin-top: 18px; }
.reference-card { margin-top: 18px; }
.reference-note { margin: 0 0 14px; color: var(--text-soft); font-size: 12px; line-height: 1.7; }
.reference-groups { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px; }
.reference-group { border: 1px solid var(--line); border-radius: 10px; padding: 14px; background: var(--surface-soft); }
.reference-group-title { margin: 0 0 10px; font-size: 12px; font-weight: 700; color: var(--text); }
.reference-items { display: grid; gap: 10px; }
.reference-item { display: grid; gap: 2px; }
.reference-item-name { margin: 0; font-size: 11px; color: var(--muted); }
.reference-item-value { margin: 0; font-size: 15px; color: var(--text); font-variant-numeric: tabular-nums; }
.reference-item-unit { font-size: 11px; color: var(--muted); font-weight: 400; }
.reference-item-note { margin: 0; font-size: 11px; color: var(--text-soft); line-height: 1.6; }
.reference-item-source { margin: 2px 0 0; font-size: 10px; color: var(--muted); }
.align-right { text-align: right; }
@media (max-width: 900px) { .item-row { grid-template-columns: minmax(0, 1fr) 68px 34px 32px; } }
@media (max-width: 640px) { .result-tiles { grid-template-columns: 1fr; } }
</style>
