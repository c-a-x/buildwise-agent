<script setup lang="ts">
/** 工友关怀：天气/环境输入 → CareAgent 高温分级 + 中暑风险 + 温馨提醒，红色高温联动语音广播。 */

import { computed, onMounted, onUnmounted, ref } from 'vue'

import { hardwareApi } from '@/api/hardware'
import { getApiError } from '@/api/http'
import { wellbeingApi } from '@/api/wellbeing'
import { ensureAlertAudio, startAlert, stopAlert } from '@/lib/alarmSound'
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageHeader from '@/components/common/AppPageHeader.vue'
import AppState from '@/components/common/AppState.vue'
import { useAppStore } from '@/stores/app'
import { useProjectStore } from '@/stores/project'
import { formatDateTime } from '@/utils/date'
import type { CareCity, WellbeingAnalysisResult, WellbeingRecordSummary, WellbeingSchedule, WellbeingTips, WeatherSnapshot } from '@/types/wellbeing'
import type { HardwareTelemetry } from '@/types/hardware'

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
const cities = ref<CareCity[]>([])
const selectedCity = ref('')
const schedule = ref<WellbeingSchedule | null>(null)
const hardware = ref<HardwareTelemetry | null>(null)
const hardwareLoading = ref(true)
const hardwareError = ref('')
const noiseDb = ref<number | null>(null)
const noiseActive = ref(false)
const noiseError = ref('')
let hardwareTimer: number | undefined
let noiseTimer: number | undefined
let audioContext: AudioContext | null = null
let noiseStream: MediaStream | null = null
let noiseAnalyser: AnalyserNode | null = null
let noiseData: Uint8Array<ArrayBuffer> | null = null

const modePill = computed(() => (result.value?.is_simulated ? '兜底规则' : '标准规则'))
const heatBadge = computed(() => result.value?.heat_level ?? 'none')
const noiseStatus = computed(() => noiseSafety(noiseDb.value))
const analysisSourceLabel = computed(() => (hardware.value?.is_fresh ? '分析采用现场传感器' : weather.value?.available ? '分析采用和风天气' : '等待环境数据'))

// 本地蜂鸣：橙色/红色高温（≥37℃）在浏览器本机响铃，无需任何硬件或后端配置
const BUZZER_LEVELS = ['orange', 'red'] as const
const alarmActive = ref(false)

function syncAlarmSound(): void {
  const shouldBuzz = result.value?.heat_level
    ? (BUZZER_LEVELS as readonly string[]).includes(result.value.heat_level)
    : false
  if (shouldBuzz) {
    startAlert()
    alarmActive.value = true
  } else {
    stopAlert()
    alarmActive.value = false
  }
}

function stopBuzzer(): void {
  stopAlert()
  alarmActive.value = false
}

onUnmounted(stopBuzzer)

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

async function loadWeather(city?: string): Promise<void> {
  weatherLoading.value = true
  try {
    weather.value = await wellbeingApi.weather(city || selectedCity.value || undefined)
    if (weather.value.available && !hardware.value?.is_fresh) fillAnalysisFromWeather()
  } catch (cause) {
    weather.value = {
      available: false,
      reason: '外部天气接口暂时不可用，现场传感器数据仍可正常显示。',
      provider: 'qweather',
      temperature_c: null,
      humidity_pct: null,
      condition: null,
      city: null,
      observed_at: null,
      is_simulated: true,
    }
  } finally {
    weatherLoading.value = false
  }
}

async function loadCities(): Promise<void> {
  try {
    cities.value = await wellbeingApi.cities()
    const initial = weather.value?.city
    selectedCity.value = initial && cities.value.some((city) => city.id === initial) ? initial : (cities.value[0]?.id ?? '')
  } catch {
    cities.value = []
  }
}

async function loadStatus(): Promise<void> {
  try {
    schedule.value = (await wellbeingApi.status()).schedule
  } catch {
    schedule.value = null
  }
}

function onCityChange(): void {
  void loadWeather(selectedCity.value)
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
  ensureAlertAudio() // 在用户点击手势内解锁 AudioContext
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
      city: weather.value?.available ? selectedCity.value : undefined,
    })
    syncAlarmSound()
    const actions: string[] = []
    if (result.value.broadcast) actions.push('现场语音广播')
    if (result.value.buzzer) actions.push('现场蜂鸣器')
    if (alarmActive.value) actions.push('本地蜂鸣器')
    app.showNotice(actions.length ? `关怀分析完成 · 已联动${actions.join('、')}` : '关怀分析完成')
    await loadRecords()
  } catch (cause) {
    localError.value = getApiError(cause)
  } finally {
    analyzing.value = false
  }
}

async function analyzeWithLiveWeather(): Promise<void> {
  ensureAlertAudio() // 一键分析前先解锁，确保 await 后仍能在手势内出声
  if (!weather.value?.available) return
  await loadWeather(selectedCity.value)
  await analyze()
}

async function viewRecord(recordId: string): Promise<void> {
  localError.value = ''
  try {
    result.value = await wellbeingApi.record(recordId)
    syncAlarmSound()
  } catch (cause) {
    localError.value = getApiError(cause)
  }
}

function fmt(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return value.toFixed(digits)
}

async function loadHardware(): Promise<void> {
  try {
    hardware.value = await hardwareApi.latest()
    hardwareError.value = ''
    if (hardware.value?.is_fresh) {
      temperatureC.value = String(hardware.value.temperature_c)
      humidityPct.value = String(hardware.value.humidity_pct)
      condition.value = '现场传感器'
    }
  } catch {
    hardwareError.value = '现场传感器接口暂时不可用，请确认后端已启动。'
    if (!temperatureC.value) fillAnalysisFromWeather()
  } finally {
    hardwareLoading.value = false
  }
}

function fillAnalysisFromWeather(): void {
  if (!weather.value?.available) return
  temperatureC.value = String(weather.value.temperature_c ?? '')
  humidityPct.value = String(weather.value.humidity_pct ?? '50')
  condition.value = weather.value.condition ?? '晴'
}

function noiseLevelLabel(value: number | null): string {
  if (value === null) return '未开启'
  if (value < 55) return '安静'
  if (value < 70) return '正常'
  if (value < 85) return '偏吵'
  return '高噪音'
}

function noiseSafety(value: number | null): { level: 'idle' | 'normal' | 'notice' | 'protect' | 'stop'; title: string; action: string; ppe: string; note: string } {
  if (value === null) {
    return {
      level: 'idle',
      title: '等待噪音检测',
      action: '开启麦克风后，系统会按现场噪音实时给出作业建议。',
      ppe: '准备防噪耳塞或耳罩',
      note: '电脑麦克风读数用于现场辅助判断，正式验收建议配合专业声级计校准。',
    }
  }
  if (value < 70) {
    return {
      level: 'normal',
      title: '噪音处于可接受范围',
      action: '可正常作业，持续观察设备启动、切割、打磨等瞬时噪音。',
      ppe: '普通安全帽与常规劳保用品',
      note: '建议保持通道沟通清晰，避免长时间靠近强噪声设备。',
    }
  }
  if (value < 85) {
    return {
      level: 'notice',
      title: '噪音偏高，缩短连续暴露',
      action: '安排轮换作业，减少人员在声源旁停留时间。',
      ppe: '建议佩戴防噪耳塞',
      note: '对混凝土切割、冲击钻、空压机附近人员进行重点提醒。',
    }
  }
  if (value < 90) {
    return {
      level: 'protect',
      title: '达到听力防护阈值',
      action: '进入该区域必须佩戴防噪耳塞或耳罩，并限制连续作业时长。',
      ppe: '必须佩戴 SNR 25dB 以上耳塞/耳罩',
      note: '现场安全员应确认警示牌、隔离带和人员轮换安排。',
    }
  }
  return {
    level: 'stop',
    title: '高噪声，建议暂停作业',
    action: '立即停止非必要高噪声作业，人员撤离到低噪声区域，复核设备和声源。',
    ppe: '复工前必须佩戴耳罩，可叠加耳塞',
    note: '复测低于 85dB 且防护到位后，再由安全员确认是否恢复作业。',
  }
}

function refreshNoise(): void {
  if (!noiseAnalyser || !noiseData) return
  noiseAnalyser.getByteTimeDomainData(noiseData)
  let sum = 0
  for (const item of noiseData) {
    const centered = (item - 128) / 128
    sum += centered * centered
  }
  const rms = Math.sqrt(sum / noiseData.length)
  noiseDb.value = Math.round(Math.max(30, Math.min(100, 20 * Math.log10(rms || 0.00001) + 94)))
}

async function startNoiseMonitor(): Promise<void> {
  noiseError.value = ''
  try {
    noiseStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    audioContext = new AudioContext()
    const source = audioContext.createMediaStreamSource(noiseStream)
    noiseAnalyser = audioContext.createAnalyser()
    noiseAnalyser.fftSize = 1024
    noiseData = new Uint8Array(new ArrayBuffer(noiseAnalyser.fftSize))
    source.connect(noiseAnalyser)
    noiseActive.value = true
    refreshNoise()
    noiseTimer = window.setInterval(refreshNoise, 200)
  } catch (cause) {
    noiseError.value = cause instanceof Error ? cause.message : '麦克风权限未开启'
    noiseActive.value = false
  }
}

function stopNoiseMonitor(): void {
  if (noiseTimer) window.clearInterval(noiseTimer)
  noiseTimer = undefined
  noiseStream?.getTracks().forEach((track) => track.stop())
  noiseStream = null
  void audioContext?.close()
  audioContext = null
  noiseAnalyser = null
  noiseData = null
  noiseActive.value = false
}

onMounted(async () => {
  if (!projects.projects.length) await projects.loadProjects()
  await loadWeather() // 先用后端默认城市取一次实时天气，weather.city 用于初始化城市下拉
  await Promise.all([loadCities(), loadRecords(), loadStatus(), loadHardware()])
  hardwareTimer = window.setInterval(loadHardware, 500)
  try {
    tips.value = await wellbeingApi.tips()
  } catch {
    tips.value = null
  }
})

onUnmounted(() => {
  if (hardwareTimer) window.clearInterval(hardwareTimer)
  stopNoiseMonitor()
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

          <div class="form-field">
            <label>查询城市</label>
            <select v-model="selectedCity" @change="onCityChange">
              <option v-if="!cities.length" value="">默认城市</option>
              <option v-for="city in cities" :key="city.id" :value="city.id">{{ city.name }}</option>
            </select>
          </div>

          <div class="weather-card" :class="{ 'is-live': weather?.available }">
            <div class="weather-card-head">
              <AppIcon name="sun" :size="16" />
              <strong>{{ weather?.available ? `实时天气 · ${weather.city}` : '实时天气' }}</strong>
              <span v-if="weatherLoading" class="mono">获取中…</span>
              <button v-else type="button" class="button-icon" title="刷新天气" @click="onCityChange"><AppIcon name="refresh" :size="14" /></button>
            </div>
            <template v-if="weather?.available">
              <p class="weather-live">{{ weather.condition }} · {{ fmt(weather.temperature_c) }}℃ · 湿度 {{ fmt(weather.humidity_pct, 0) }}% <span class="mono">（{{ weather.provider }}）</span></p>
              <p v-if="weather.observed_at" class="helper-text">观测时间 {{ formatDateTime(weather.observed_at) }}</p>
              <p class="helper-text">和风 API 提供城市实时天气；现场传感器数据在下方独立显示，两者并存不互相替代。</p>
            </template>
            <template v-else>
              <p class="weather-fallback">{{ weather?.reason || '正在获取实时天气…' }}</p>
              <p class="helper-text">未配置天气 API 时请在下方手动填写温度与湿度。</p>
            </template>
          </div>

          <div class="live-site-card">
            <div class="weather-card-head">
              <AppIcon name="mic" :size="16" />
              <strong>现场实时环境</strong>
              <span class="mono">{{ hardwareLoading ? '读取中…' : hardware?.is_fresh ? 'ESP32 在线' : '等待数据' }}</span>
            </div>
            <div class="live-metrics">
              <div class="live-metric">
                <small>温度</small>
                <strong>{{ hardware ? `${fmt(hardware.temperature_c)}℃` : '—' }}</strong>
              </div>
              <div class="live-metric">
                <small>湿度</small>
                <strong>{{ hardware ? `${fmt(hardware.humidity_pct, 0)}%` : '—' }}</strong>
              </div>
              <div class="live-metric">
                <small>噪音</small>
                <strong>{{ noiseDb === null ? '—' : `${noiseDb} dB` }}</strong>
              </div>
            </div>
            <div class="noise-actions">
              <button v-if="!noiseActive" type="button" class="secondary-button" @click="startNoiseMonitor"><AppIcon name="mic" :size="15" />开启噪音检测</button>
              <button v-else type="button" class="secondary-button" @click="stopNoiseMonitor"><AppIcon name="close" :size="15" />停止噪音检测</button>
              <span class="mono">{{ noiseLevelLabel(noiseDb) }}</span>
            </div>
            <div class="noise-safety-card" :class="`noise-${noiseStatus.level}`">
              <div>
                <small>噪音作业建议</small>
                <strong>{{ noiseStatus.title }}</strong>
              </div>
              <p>{{ noiseStatus.action }}</p>
              <ul class="noise-rule-list">
                <li><AppIcon name="check" :size="14" /><span>{{ noiseStatus.ppe }}</span></li>
                <li><AppIcon name="info" :size="14" /><span>{{ noiseStatus.note }}</span></li>
              </ul>
            </div>
            <p v-if="hardwareError" class="helper-text">{{ hardwareError }}</p>
            <p v-if="noiseError" class="helper-text">{{ noiseError }}</p>
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

          <button type="button" class="secondary-button button-block" :disabled="analyzing || !weather?.available || weatherLoading" @click="analyzeWithLiveWeather">
            <AppIcon name="spark" :size="16" />用实时天气一键分析
          </button>
          <button type="button" class="secondary-button button-block" @click="fillSample"><AppIcon name="sun" :size="16" />填入示例天气</button>
          <p v-if="localError" class="error-text">{{ localError }}</p>
          <button type="button" class="primary-button button-block" :disabled="analyzing" @click="analyze">
            <AppIcon name="spark" :size="16" />{{ analyzing ? '分析中…' : '开始关怀分析' }}
          </button>
          <p class="helper-text">高温分级与作业限制依据《防暑降温措施管理办法》（安监总安健〔2012〕89号）；红色高温（≥40℃）自动联动现场语音广播（已配置时），橙色/红色高温在本机自动响蜂鸣提醒。</p>
          <p class="helper-text">{{ analysisSourceLabel }}。高温分级与作业限制依据《防暑降温措施管理办法》（安监总安健〔2012〕89号）；红色高温（≥40℃）自动联动现场语音广播。</p>
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
              <p v-if="result.auto || result.weather_source?.city" class="source-note">
                <template v-if="result.auto"><AppIcon name="clock" :size="13" />系统定时关怀</template>
                <template v-if="result.weather_source?.city"><AppIcon name="sun" :size="13" />{{ result.weather_source.city }}<template v-if="result.weather_source.provider"> · {{ result.weather_source.provider }}</template><template v-if="result.weather_source.observed_at"> · {{ result.weather_source.observed_at }}</template></template>
              </p>
              <span v-if="result.broadcast" class="broadcast-note"><AppIcon name="speaker" :size="14" />高温警告 · 已联动现场语音广播</span>
              <span v-if="result.buzzer" class="broadcast-note"><AppIcon name="bell" :size="14" />高温警告 · 已联动现场蜂鸣器</span>
              <button v-if="alarmActive" type="button" class="buzzer-stop" @click="stopBuzzer"><AppIcon name="bell" :size="14" />本地蜂鸣响铃中 · 点击停止</button>
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
            <div class="card-head"><div><p class="section-kicker">NOISE CONTROL</p><h3>噪音防护与停工建议</h3></div><span class="mono">{{ noiseDb === null ? '未检测' : `${noiseDb} dB` }}</span></div>
            <div class="noise-result" :class="`noise-${noiseStatus.level}`">
              <strong>{{ noiseStatus.title }}</strong>
              <p>{{ noiseStatus.action }}</p>
            </div>
            <ul class="clean-list noise-clean-list">
              <li><AppIcon name="check" :size="15" /><span>{{ noiseStatus.ppe }}</span></li>
              <li><AppIcon name="info" :size="15" /><span>70dB 以上加强提醒，85dB 以上必须听力防护，90dB 以上建议暂停高噪声作业并复测。</span></li>
            </ul>
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

    <section v-if="schedule" class="card schedule-card">
      <div class="card-head"><div><p class="section-kicker">SCHEDULE</p><h3>定时关怀</h3></div><span class="mono">{{ schedule.enabled ? `每日 ${schedule.time}` : '未启用' }}</span></div>
      <p class="schedule-text">
        <template v-if="schedule.enabled">每天 <b>{{ schedule.time }}</b> 按{{ schedule.city || '配置城市' }}预报的当日最高气温自动评估高温等级并写入关怀历史，橙/红色高温自动联动现场语音广播。</template>
        <template v-else>未启用定时关怀，可在后端配置 CARE_SCHEDULE_ENABLED=true 开启。</template>
        <small v-if="schedule.last_run_at">最近执行：{{ schedule.last_run_at }}{{ schedule.last_result ? ' · ' + schedule.last_result : '' }}</small>
      </p>
    </section>

    <section class="card history-card">
      <div class="card-head"><div><p class="section-kicker">HISTORY</p><h3>关怀历史</h3></div><span class="mono">{{ records.length }} 条</span></div>
      <div v-if="recordsLoading" class="table-wrap"><div class="loading-dots">正在加载历史</div></div>
      <div v-else-if="!records.length" class="table-wrap"><p class="muted-copy">暂无关怀记录，完成一次分析后这里会显示历史清单。</p></div>
      <div v-else class="table-wrap">
        <table class="data-table">
          <thead><tr><th>分析编号</th><th>项目</th><th>来源</th><th>高温等级</th><th class="align-right">中暑风险</th><th>时间</th><th class="action-cell">操作</th></tr></thead>
          <tbody>
            <tr v-for="entry in records" :key="entry.analysis_id">
              <td><strong>{{ entry.analysis_id }}</strong><small>{{ entry.heat_index ? `体感 ${fmt(entry.heat_index)}℃` : '—' }}</small></td>
              <td>{{ entry.project_name }}</td>
              <td><span v-if="entry.auto" class="auto-badge">定时</span><span>{{ entry.city || '—' }}</span></td>
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
.live-site-card { border: 1px solid var(--line); border-radius: 10px; padding: 11px 13px; display: grid; gap: 10px; background: var(--surface); }
.live-metrics { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
.live-metric { min-height: 58px; border: 1px solid var(--line); border-radius: 8px; padding: 8px 9px; background: var(--surface-soft); display: grid; align-content: center; gap: 3px; }
.live-metric small { font-size: 10px; color: var(--muted); }
.live-metric strong { font-size: 18px; line-height: 1.1; color: var(--text); }
.noise-actions { display: flex; align-items: center; gap: 8px; }
.noise-actions .secondary-button { min-height: 32px; padding: 0 10px; }
.live-site-card .helper-text { margin: 0; color: var(--muted); font-size: 10px; }
.noise-safety-card { display: grid; gap: 7px; border: 1px solid var(--line); border-radius: 8px; padding: 10px 11px; background: var(--surface-soft); }
.noise-safety-card small { display: block; margin-bottom: 3px; color: var(--muted); font-size: 10px; }
.noise-safety-card strong { color: var(--text); font-size: 12px; }
.noise-safety-card p { margin: 0; color: var(--text-soft); font-size: 11px; line-height: 1.55; }
.noise-rule-list { display: grid; gap: 5px; padding: 0; margin: 0; list-style: none; }
.noise-rule-list li { display: flex; align-items: flex-start; gap: 6px; color: var(--muted); font-size: 10px; line-height: 1.45; }
.noise-rule-list .app-icon { flex: none; margin-top: 1px; color: currentColor; }
.noise-result { display: grid; gap: 6px; border: 1px solid var(--line); border-radius: 8px; padding: 12px 13px; background: var(--surface-soft); }
.noise-result strong { font-size: 13px; color: var(--text); }
.noise-result p { margin: 0; color: var(--text-soft); font-size: 12px; line-height: 1.6; }
.noise-clean-list { margin-top: 12px; }
.noise-idle { border-color: var(--line); background: var(--surface-soft); }
.noise-normal { border-color: var(--success); background: var(--success-bg); }
.noise-notice { border-color: var(--warning); background: var(--warning-bg); }
.noise-protect { border-color: var(--danger); background: var(--danger-bg); }
.noise-stop { border-color: var(--critical); background: var(--critical-bg); }
.noise-stop strong, .noise-stop p, .noise-stop li { color: var(--critical); }
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
.buzzer-stop { display: inline-flex; align-items: center; gap: 5px; margin-top: 6px; padding: 4px 10px; border: 1px solid var(--danger); border-radius: 999px; background: var(--surface); color: var(--danger); font-size: 11px; font-weight: 700; cursor: pointer; }
.buzzer-stop:hover { background: var(--danger); color: #fff; }
.buzzer-stop .app-icon { flex: none; }
.source-note { display: inline-flex; align-items: center; flex-wrap: wrap; gap: 6px; margin: 5px 0 0; color: var(--text-soft); font-size: 11px; }
.source-note .app-icon { flex: none; color: var(--blue); }
.auto-badge { display: inline-block; margin-right: 6px; padding: 1px 6px; border-radius: 999px; border: 1px solid var(--accent); color: var(--accent); font-size: 10px; font-weight: 700; }
.schedule-card { margin-bottom: 18px; }
.schedule-text { margin: 0; font-size: 12px; color: var(--text-soft); line-height: 1.7; }
.schedule-text b { color: var(--text); }
.schedule-text small { display: block; margin-top: 4px; color: var(--muted); font-size: 11px; }
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
