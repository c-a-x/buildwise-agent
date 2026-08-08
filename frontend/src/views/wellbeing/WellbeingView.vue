<script setup lang="ts">
/** 工友关怀：天气/环境输入 → CareAgent 高温分级 + 中暑风险 + 温馨提醒，红色高温联动语音广播。 */

import { computed, onMounted, ref } from 'vue'

import { getApiError } from '@/api/http'
import { wellbeingApi } from '@/api/wellbeing'
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageHeader from '@/components/common/AppPageHeader.vue'
import AppState from '@/components/common/AppState.vue'
import { useAppStore } from '@/stores/app'
import { useProjectStore } from '@/stores/project'
import { formatDateTime } from '@/utils/date'
import type { WellbeingAnalysisResult, WellbeingRecordSummary, WellbeingTips, WeatherSnapshot } from '@/types/wellbeing'

const CONDITIONS = ['晴', '多云', '阴', '小雨', '中雨', '雷阵雨']

const app = useAppStore()
const projects = useProjectStore()

const temperatureC = ref('')
const humidityPct = ref('50')
const condition = ref('晴')
const description = ref('')
const analyzing = ref(false)
const localError = ref('')

const result = ref<WellbeingAnalysisResult | null>(null)
const records = ref<WellbeingRecordSummary[]>([])
const recordsLoading = ref(false)
const tips = ref<WellbeingTips | null>(null)
const weather = ref<WeatherSnapshot | null>(null)
const weatherLoading = ref(true)

const modePill = computed(() => (result.value?.is_simulated ? '兜底规则' : '标准规则'))
const heatBadge = computed(() => result.value?.heat_level ?? 'none')

function heatLabel(level: string): string {
  return { none: '无高温', yellow: '黄色预警', orange: '橙色预警', red: '红色预警' }[level] ?? level
}

function riskTierLabel(riskIndex: number): string {
  if (riskIndex < 30) return '低风险'
  if (riskIndex < 50) return '中风险'
  if (riskIndex < 75) return '高风险'
  return '极高风险'
}

function selectProject(event: Event): void {
  projects.selectProject((event.target as HTMLSelectElement).value)
  void loadRecords()
}

function fillSample(): void {
  temperatureC.value = '36'
  humidityPct.value = '65'
  condition.value = '晴'
  description.value = '一号楼西侧屋面钢筋绑扎作业面'
  localError.value = ''
}

async function loadWeather(): Promise<void> {
  weatherLoading.value = true
  try {
    weather.value = await wellbeingApi.weather()
    if (weather.value.available) {
      temperatureC.value = String(weather.value.temperature_c ?? '')
      humidityPct.value = String(weather.value.humidity_pct ?? '50')
      condition.value = weather.value.condition ?? '晴'
    }
  } catch (cause) {
    weather.value = { available: false, reason: getApiError(cause), provider: null, temperature_c: null, humidity_pct: null, condition: null, city: null, observed_at: null, is_simulated: true }
  } finally {
    weatherLoading.value = false
  }
}

async function loadRecords(): Promise<void> {
  recordsLoading.value = true
  try {
    records.value = await wellbeingApi.records(projects.currentProject?.id)
  } catch {
    records.value = []
  } finally {
    recordsLoading.value = false
  }
}

async function analyze(): Promise<void> {
  localError.value = ''
  const temp = Number(temperatureC.value)
  const humidity = Number(humidityPct.value)
  if (!projects.currentProject?.id) { localError.value = '当前没有可用项目'; return }
  if (Number.isNaN(temp)) { localError.value = '请填写有效的温度（℃）'; return }
  if (Number.isNaN(humidity) || humidity < 0 || humidity > 100) { localError.value = '请填写 0~100 的湿度（%）'; return }
  analyzing.value = true
  try {
    result.value = await wellbeingApi.analyze({
      project_id: projects.currentProject.id,
      temperature_c: temp,
      humidity_pct: humidity,
      condition: condition.value,
      description: description.value,
    })
    app.showNotice(result.value.heat_level === 'red' ? '关怀分析完成 · 已联动现场语音广播' : '关怀分析完成')
    await loadRecords()
  } catch (cause) {
    localError.value = getApiError(cause)
  } finally {
    analyzing.value = false
  }
}

async function viewRecord(recordId: string): Promise<void> {
  localError.value = ''
  try {
    result.value = await wellbeingApi.record(recordId)
  } catch (cause) {
    localError.value = getApiError(cause)
  }
}

function fmt(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return value.toFixed(digits)
}

onMounted(async () => {
  if (!projects.projects.length) await projects.loadProjects()
  await Promise.all([loadWeather(), loadRecords()])
  try {
    tips.value = await wellbeingApi.tips()
  } catch {
    tips.value = null
  }
})
</script>

<template>
  <div>
    <AppPageHeader eyebrow="WORKER WELLBEING" title="工友关怀 · 幸福工地" description="输入天气/环境数据，CareAgent 按《防暑降温措施管理办法》计算高温等级与中暑风险，送上温馨、可执行的关怀提醒。">
      <template #actions>
        <span v-if="result" class="status-pill" :class="`heat-${heatBadge}`"><span class="status-dot" :class="heatBadge !== 'none' ? 'online' : ''" />{{ heatLabel(heatBadge) }}</span>
        <span v-if="result" class="status-pill dark"><span class="status-dot online" />{{ modePill }}</span>
      </template>
    </AppPageHeader>

    <div class="safety-layout">
      <section class="card input-panel">
        <div class="card-head"><div><p class="section-kicker">01 · INPUT</p><h3>输入天气与环境</h3></div><span class="mono">CareAgent</span></div>
        <div class="form-grid">
          <div class="form-field">
            <label>所属项目</label>
            <select :value="projects.currentProject?.id" @change="selectProject">
              <option v-if="!projects.currentProject" value="">请选择项目</option>
              <option v-for="project in projects.projects" :key="project.id" :value="project.id">{{ project.name }}</option>
            </select>
          </div>

          <div class="weather-card" :class="{ 'is-live': weather?.available }">
            <div class="weather-card-head">
              <AppIcon name="sun" :size="16" />
              <strong>{{ weather?.available ? `实时天气 · ${weather.city}` : '实时天气' }}</strong>
              <span v-if="weatherLoading" class="mono">获取中…</span>
            </div>
            <template v-if="weather?.available">
              <p class="weather-live">{{ weather.condition }} · {{ fmt(weather.temperature_c) }}℃ · 湿度 {{ fmt(weather.humidity_pct, 0) }}% <span class="mono">（{{ weather.provider }}）</span></p>
              <p class="helper-text">已用实时天气预填下表，可按现场情况修改后分析。</p>
            </template>
            <template v-else>
              <p class="weather-fallback">{{ weather?.reason || '正在获取实时天气…' }}</p>
              <p class="helper-text">未配置天气 API 时请在下方手动填写温度与湿度。</p>
            </template>
          </div>

          <div class="two-fields">
            <div class="form-field">
              <label>温度（℃）</label>
              <input v-model="temperatureC" type="number" min="-50" max="60" step="0.1" placeholder="如 36" />
            </div>
            <div class="form-field">
              <label>相对湿度（%）</label>
              <input v-model="humidityPct" type="number" min="0" max="100" step="1" placeholder="如 60" />
            </div>
          </div>

          <div class="form-field">
            <label>天气现象</label>
            <select v-model="condition">
              <option v-for="item in CONDITIONS" :key="item" :value="item">{{ item }}</option>
            </select>
          </div>

          <div class="form-field">
            <label>现场说明（可选）</label>
            <input v-model="description" maxlength="300" placeholder="如 一号楼西侧屋面钢筋绑扎作业面" />
          </div>

          <button type="button" class="secondary-button button-block" @click="fillSample"><AppIcon name="sun" :size="16" />填入示例天气</button>
          <p v-if="localError" class="error-text">{{ localError }}</p>
          <button type="button" class="primary-button button-block" :disabled="analyzing" @click="analyze">
            <AppIcon name="spark" :size="16" />{{ analyzing ? '分析中…' : '开始关怀分析' }}
          </button>
          <p class="helper-text">高温分级与作业限制依据《防暑降温措施管理办法》（安监总安健〔2012〕89号）；红色高温（≥40℃）自动联动现场语音广播。</p>
        </div>
      </section>

      <div class="result-column">
        <div v-if="!result" class="card">
          <AppState type="empty" title="暂无关怀分析" description="填写天气与环境数据后点击“开始关怀分析”，这里会显示高温等级、中暑风险与温馨提醒。" />
        </div>

        <template v-else>
          <div class="heat-banner" :class="`heat-${result.heat_level}`">
            <div class="heat-banner-mark"><AppIcon name="sun" :size="26" /></div>
            <div class="heat-banner-copy">
              <p class="section-kicker">HEAT LEVEL</p>
              <h3>{{ result.heat_level_name }}</h3>
              <p>{{ result.advice }}</p>
              <span v-if="result.broadcast" class="broadcast-note"><AppIcon name="speaker" :size="14" />红色高温 · 已联动现场语音广播</span>
            </div>
          </div>

          <div class="metrics-grid result-tiles">
            <div class="metric-card"><div class="metric-top"><AppIcon class="metric-icon" name="bell" :size="18" /></div><strong>{{ result.risk_index }}</strong><p>中暑风险指数（{{ result.risk_tier }}）</p></div>
            <div class="metric-card"><div class="metric-top"><AppIcon class="metric-icon warning" name="spark" :size="18" /></div><strong>{{ fmt(result.heat_index) }}℃</strong><p>体感温度（humidex）</p></div>
            <div class="metric-card"><div class="metric-top"><AppIcon class="metric-icon" name="sun" :size="18" /></div><strong>{{ result.uv }}</strong><p>紫外线等级</p></div>
          </div>

          <section class="card">
            <div class="card-head"><div><p class="section-kicker">RESTRICTION</p><h3>作业限制</h3></div><span class="mono">{{ result.condition }} · {{ fmt(result.temperature_c) }}℃</span></div>
            <p class="restriction-text">{{ result.restriction || '未触发高温作业限制。' }}</p>
          </section>

          <section class="card">
            <div class="card-head"><div><p class="section-kicker">WARM REMINDERS</p><h3>温馨提醒</h3></div><span class="mono">{{ result.reminders.length }} 条</span></div>
            <ul class="clean-list">
              <li v-for="tip in result.reminders" :key="tip.id"><AppIcon name="check" :size="15" /><span>{{ tip.text }}</span></li>
            </ul>
            <p v-if="result.allowance" class="allowance-note"><AppIcon name="info" :size="15" /><span>{{ result.allowance }}</span></p>
            <p v-if="result.special_groups" class="allowance-note"><AppIcon name="info" :size="15" /><span>{{ result.special_groups }}</span></p>
          </section>

          <section class="card">
            <div class="card-head"><div><p class="section-kicker">FIRST AID</p><h3>中暑急救知识</h3></div><span class="mono">先兆 → 重症</span></div>
            <div class="aid-list">
              <article v-for="stage in result.first_aid" :key="stage.stage" class="aid-item">
                <h4>{{ stage.stage }}</h4>
                <p><b>症状：</b>{{ stage.symptoms }}</p>
                <p><b>处置：</b>{{ stage.action }}</p>
              </article>
            </div>
          </section>

          <section v-if="result.facilities.length" class="card">
            <div class="card-head"><div><p class="section-kicker">FACILITIES</p><h3>福利设施</h3></div><span class="mono">现场保障</span></div>
            <div class="facility-list">
              <div v-for="facility in result.facilities" :key="facility.name" class="facility-item">
                <strong>{{ facility.name }}</strong>
                <span>{{ facility.location }} · {{ facility.hours }}</span>
                <small>{{ facility.note }}</small>
              </div>
            </div>
          </section>
        </template>
      </div>
    </div>

    <section class="card history-card">
      <div class="card-head"><div><p class="section-kicker">HISTORY</p><h3>关怀历史</h3></div><span class="mono">{{ records.length }} 条</span></div>
      <div v-if="recordsLoading" class="table-wrap"><div class="loading-dots">正在加载历史</div></div>
      <div v-else-if="!records.length" class="table-wrap"><p class="muted-copy">暂无关怀记录，完成一次分析后这里会显示历史清单。</p></div>
      <div v-else class="table-wrap">
        <table class="data-table">
          <thead><tr><th>分析编号</th><th>项目</th><th>高温等级</th><th class="align-right">中暑风险</th><th>时间</th><th class="action-cell">操作</th></tr></thead>
          <tbody>
            <tr v-for="entry in records" :key="entry.analysis_id">
              <td><strong>{{ entry.analysis_id }}</strong><small>{{ entry.heat_index ? `体感 ${fmt(entry.heat_index)}℃` : '—' }}</small></td>
              <td>{{ entry.project_name }}</td>
              <td><span class="status-pill" :class="`heat-${entry.heat_level}`">{{ heatLabel(entry.heat_level) }}</span></td>
              <td class="align-right"><strong>{{ entry.risk_index }}</strong> <span class="mono">{{ riskTierLabel(entry.risk_index) }}</span></td>
              <td>{{ formatDateTime(entry.created_at) }}</td>
              <td class="action-cell"><button type="button" class="button-icon" @click="viewRecord(entry.analysis_id)">查看</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.weather-card { border: 1px dashed var(--line); border-radius: 10px; padding: 11px 13px; display: grid; gap: 5px; background: var(--surface-soft); }
.weather-card.is-live { border-style: solid; border-color: var(--success); background: var(--success-bg); }
.weather-card-head { display: flex; align-items: center; gap: 7px; }
.weather-card-head .app-icon { color: var(--accent); }
.weather-card-head strong { font-size: 12px; color: var(--text-soft); }
.weather-card-head .mono { margin-left: auto; color: var(--muted); font-size: 10px; }
.weather-live { margin: 0; font-size: 12px; color: var(--text); }
.weather-fallback { margin: 0; font-size: 12px; color: var(--danger); }
.weather-card .helper-text { margin: 0; color: var(--muted); font-size: 10px; }
.result-tiles { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.heat-banner { display: flex; align-items: flex-start; gap: 15px; padding: 18px 20px; border-radius: 12px; border: 1px solid var(--line); background: var(--surface-soft); }
.heat-banner.heat-none { border-color: var(--success); background: var(--success-bg); }
.heat-banner.heat-yellow { border-color: var(--warning); background: var(--warning-bg); }
.heat-banner.heat-orange { border-color: var(--danger); background: var(--danger-bg); }
.heat-banner.heat-red { border-color: var(--critical); background: var(--critical-bg); }
.heat-banner-mark { display: grid; width: 48px; height: 48px; place-items: center; border-radius: 12px; flex: none; color: var(--accent); background: var(--surface); border: 1px solid var(--line); }
.heat-red .heat-banner-mark { color: var(--danger); }
.heat-banner-copy { display: grid; gap: 4px; }
.heat-banner-copy .section-kicker { margin: 0; }
.heat-banner-copy h3 { margin: 0; font-size: 20px; font-weight: 800; color: var(--text); }
.heat-banner-copy p:not(.section-kicker) { margin: 0; font-size: 12px; color: var(--text-soft); line-height: 1.6; }
.broadcast-note { display: inline-flex; align-items: center; gap: 5px; margin-top: 4px; color: var(--danger); font-size: 11px; font-weight: 700; }
.broadcast-note .app-icon { flex: none; }
.restriction-text { margin: 0; font-size: 12px; color: var(--text-soft); line-height: 1.7; }
.allowance-note { display: flex; align-items: flex-start; gap: 7px; margin: 8px 0 0; color: var(--text-soft); font-size: 11px; line-height: 1.6; }
.allowance-note .app-icon { flex: none; margin-top: 1px; color: var(--blue); }
.aid-list { display: grid; gap: 10px; }
.aid-item { border: 1px solid var(--line); border-radius: 10px; padding: 11px 13px; background: var(--surface); }
.aid-item h4 { margin: 0 0 5px; font-size: 12px; font-weight: 800; color: var(--text); }
.aid-item p { margin: 2px 0 0; font-size: 11px; color: var(--muted); line-height: 1.6; }
.aid-item b { color: var(--text-soft); }
.facility-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.facility-item { display: grid; gap: 2px; border: 1px solid var(--line); border-radius: 10px; padding: 11px 13px; background: var(--surface); }
.facility-item strong { font-size: 12px; color: var(--text); }
.facility-item span { font-size: 11px; color: var(--text-soft); }
.facility-item small { font-size: 10px; color: var(--muted); }
.history-card { margin-top: 18px; }
.align-right { text-align: right; }
.status-pill.heat-none { color: var(--success); border-color: var(--success); background: var(--success-bg); }
.status-pill.heat-yellow { color: var(--accent); border-color: var(--accent); background: var(--accent-soft); }
.status-pill.heat-orange { color: var(--danger); border-color: var(--danger); background: var(--danger-bg); }
.status-pill.heat-red { color: var(--critical); border-color: var(--critical); background: var(--critical-bg); }
@media (max-width: 640px) { .result-tiles { grid-template-columns: 1fr; } .facility-list { grid-template-columns: 1fr; } }
</style>
