<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { getApiError } from '@/api/http'
import { workOrdersApi } from '@/api/workOrders'
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageHeader from '@/components/common/AppPageHeader.vue'
import AppState from '@/components/common/AppState.vue'
import DetectionPreview from '@/components/safety/DetectionPreview.vue'
import sampleQualityCrack from '@/assets/samples/quality_1_crack.jpg'
import sampleQualityLeakage from '@/assets/samples/quality_2_leakage.jpg'
import sampleQualityAbscission from '@/assets/samples/quality_3_abscission.jpg'
import { useAppStore } from '@/stores/app'
import { useProjectStore } from '@/stores/project'
import { useQualityStore } from '@/stores/quality'
import { formatDateTime } from '@/utils/date'
import { riskLabel } from '@/utils/risk'
import { taskIdFromQuery } from '@/utils/safetyHistory'

const route = useRoute()
const projects = useProjectStore()
const quality = useQualityStore()
const app = useAppStore()
const file = ref<File | null>(null)
const previewUrl = ref('')
const showAnnotated = ref(false)
const location = ref('2号楼东侧外墙')
const workType = ref('外墙抹灰')
const description = ref('')
const localError = ref('')
const confirming = ref(false)
const confirmedOrderId = ref('')
const isDragging = ref(false)
const result = computed(() => quality.currentResult)
const historyTaskId = computed(() => taskIdFromQuery(route.query))
const historyMode = computed(() => Boolean(historyTaskId.value))
const assetBase = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace(/\/api\/v1\/?$/, '')
const displayImage = computed(() => {
  if (previewUrl.value) return previewUrl.value
  return result.value ? `${assetBase}${result.value.file_url}` : ''
})
// 顶部状态徽标：有分析结果时展示实际视觉 Provider，未分析时保持离线说明
const visionLabel = computed(() => {
  if (!result.value) return 'Mock Provider 在线'
  const vision = result.value.provider_info?.vision
  if (!vision) return result.value.is_simulated ? 'AI 模拟结果' : '真实模型结果'
  if (vision === 'mock') return 'Mock Provider 在线'
  const parts = vision.replace(/^quality_hybrid:?/, '').split('+').filter(Boolean).map(shortenVisionPart)
  return `模型在线 · ${parts.length ? parts.join(' + ') : vision}`
})
const isOfflineSimulated = computed(() => !result.value || result.value.is_simulated)

// 缺陷按来源拆分：YOLO/mock 归「识别到的缺陷」，LLM 归「深度分析」专属卡片
const yoloDefects = computed(() => (result.value?.defects ?? []).filter((defect) => defect.source !== 'llm'))
const visionLlmDefects = computed(() => (result.value?.defects ?? []).filter((defect) => defect.source === 'llm'))
const visionLlmProvider = computed(() => result.value?.provider_info?.vision_llm_provider ?? '')
const visionLlmEnabled = computed(() => result.value?.provider_info?.vision_llm_enabled === 'true')
const visionLlmHasStatus = computed(() => Boolean(visionLlmProvider.value) || visionLlmDefects.value.length > 0)
const visionLlmProviderLabel = computed(() => {
  const provider = visionLlmProvider.value
  if (provider === 'doubao') return '豆包'
  if (provider === 'claude_cli') return 'Claude CLI'
  return provider || 'LLM'
})
const llmNoteTitle = computed(() => {
  if (!result.value) return '当前为离线模拟模式'
  if (isOfflineSimulated.value) return '当前为离线模拟模式'
  return visionLlmEnabled.value ? '当前使用真实检测模型 + LLM 深度分析' : '当前使用真实检测模型'
})
const llmNoteText = computed(() => {
  if (!result.value || isOfflineSimulated.value) {
    return 'QualityAgent 使用本地规则；RagAgent 使用内置质量规范条目；不会调用付费模型。'
  }
  if (visionLlmEnabled.value) {
    return 'QualityAgent 使用 YOLO 识别墙体缺陷；Vision LLM 提供 D1-D5 深层缺陷分析与修复建议。'
  }
  return 'QualityAgent 使用 YOLO 目标检测识别裂缝/渗漏/剥落/锈蚀/鼓包；RagAgent 使用内置规范条目；LLM 未配置时自动降级，不调用付费模型。'
})

function shortenVisionPart(part: string): string {
  if (part === 'yolo') return 'YOLO'
  if (part === 'doubao') return '豆包 LLM'
  if (part === 'claude' || part === 'claude_cli') return 'Claude LLM'
  return part
}

function sourceLabel(source: string): string {
  if (source === 'yolo') return 'YOLO 检测'
  if (source === 'llm') return 'LLM 分析'
  return source
}

function selectProject(event: Event): void {
  projects.selectProject((event.target as HTMLSelectElement).value)
}

async function loadHistoryTask(): Promise<void> {
  const taskId = historyTaskId.value
  if (!taskId) return
  localError.value = ''
  try { await quality.loadTask(taskId) } catch (cause) { localError.value = getApiError(cause) }
}

onMounted(async () => {
  if (!projects.projects.length) await projects.loadProjects()
  await loadHistoryTask()
})
watch(() => route.query.task, () => { void loadHistoryTask() })

function handleFile(event: Event): void {
  const selected = (event.target as HTMLInputElement).files?.[0]
  acceptFile(selected)
}

function acceptFile(candidate: File | undefined): void {
  if (!candidate) return
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(candidate.type)) {
    localError.value = '仅支持 JPEG、PNG、WEBP 图片'
    return
  }
  if (candidate.size > 10 * 1024 * 1024) {
    localError.value = '图片大小不能超过 10 MB'
    return
  }
  localError.value = ''
  file.value = candidate
  previewUrl.value = URL.createObjectURL(candidate)
  quality.clearResult()
  confirmedOrderId.value = ''
}

const samples = [
  { url: sampleQualityCrack, name: '墙面裂缝', hint: '示例 · crack', file: 'quality_1_crack.jpg' },
  { url: sampleQualityLeakage, name: '顶板渗漏', hint: '示例 · leakage', file: 'quality_2_leakage.jpg' },
  { url: sampleQualityAbscission, name: '外墙剥落', hint: '示例 · abscission', file: 'quality_3_abscission.jpg' },
]

async function loadSample(sampleUrl: string, fileName: string): Promise<void> {
  try {
    const response = await fetch(sampleUrl)
    const blob = await response.blob()
    acceptFile(new File([blob], fileName, { type: blob.type || 'image/jpeg' }))
  } catch (cause) { localError.value = getApiError(cause) }
}

function handleDragOver(): void { isDragging.value = true }
function handleDragLeave(): void { isDragging.value = false }
function handleDrop(event: DragEvent): void {
  isDragging.value = false
  acceptFile(event.dataTransfer?.files?.[0])
}

async function analyze(): Promise<void> {
  localError.value = ''
  if (!file.value) { localError.value = '请先选择一张工程部位图片'; return }
  if (!projects.currentProject?.id) { localError.value = '当前没有可用项目'; return }
  try {
    await quality.analyze(file.value, { project_id: projects.currentProject.id, location: location.value, work_type: workType.value, description: description.value })
  } catch (cause) { localError.value = getApiError(cause) }
}

async function confirmOrder(): Promise<void> {
  if (!result.value?.work_order_draft || confirmedOrderId.value) return
  confirming.value = true
  localError.value = ''
  try {
    const order = await workOrdersApi.create(result.value.task_id)
    confirmedOrderId.value = order.id
    app.showNotice('工单已确认创建，可在整改工单中继续流转')
  } catch (cause) { localError.value = getApiError(cause) } finally { confirming.value = false }
}

function confidence(value: number): string { return `${Math.round(value * 100)}%` }
</script>

<template>
  <div><AppPageHeader eyebrow="QUALITY INSPECTION" title="质量巡检分析" description="上传工程部位图片，让五个离线 Agent 协同完成缺陷识别、规范检索、整改工单和复检提醒。"><template #actions><span class="status-pill dark"><span class="status-dot online" />{{ visionLabel }}</span></template></AppPageHeader>
    <div class="safety-layout">
      <section class="card input-panel"><div class="card-head"><div><p class="section-kicker">01 · INPUT</p><h3>准备一次质量巡检</h3></div><span class="mono">120s timeout</span></div><div class="form-grid">
        <div class="form-field"><label>当前项目</label><select :value="projects.currentProject?.id" @change="selectProject"><option v-for="project in projects.projects" :key="project.id" :value="project.id">{{ project.name }}</option></select></div>
        <div class="form-field"><label>巡检图片 <span>*</span></label><label class="upload-zone" :class="{ 'is-dragging': isDragging }" @dragover.prevent="handleDragOver" @dragleave.prevent="handleDragLeave" @drop.prevent="handleDrop"><input type="file" accept="image/jpeg,image/png,image/webp" @change="handleFile" /><img v-if="previewUrl" :src="previewUrl" alt="已选择的巡检图片预览" /><span v-else class="upload-icon"><AppIcon name="upload" :size="22" /></span><strong>{{ file ? '重新选择巡检图片' : '点击或拖拽上传巡检图片' }}</strong><small>JPEG / PNG / WEBP · 最大 10 MB</small><span v-if="file" class="file-name">{{ file.name }}</span></label><p v-if="historyMode" class="helper-text">正在查看历史任务 {{ historyTaskId }}，无需再次上传；选择新图片后可重新分析。</p></div>
        <div class="form-field"><label>示例图片 <span>点击即用</span></label><div class="sample-row"><button v-for="sample in samples" :key="sample.file" type="button" class="sample-card" @click="loadSample(sample.url, sample.file)"><img :src="sample.url" alt="示例图片" /><span class="sample-name">{{ sample.name }}</span><small class="sample-hint">{{ sample.hint }}</small></button></div></div>
        <div class="two-fields"><div class="form-field"><label for="location">巡检部位</label><input id="location" v-model.trim="location" placeholder="如：2号楼东侧外墙" /></div><div class="form-field"><label for="work-type">作业类型</label><input id="work-type" v-model.trim="workType" placeholder="如：外墙抹灰" /></div></div>
        <div class="form-field"><label for="description">现场说明 <span>可选</span></label><textarea id="description" v-model.trim="description" placeholder="补充结构部位、龄期或需要重点关注的信息" /></div>
        <div v-if="localError || quality.error" class="alert alert-error" role="alert">{{ localError || quality.error }}</div>
        <button v-if="!historyMode || file" class="primary-button analyze-button button-block" type="button" :disabled="quality.analyzing || quality.loadingTask" @click="analyze"><AppIcon :name="quality.analyzing ? 'refresh' : 'spark'" :size="16" />{{ quality.analyzing ? 'Agent 正在协同分析…' : historyMode ? '使用新图片重新分析' : '开始质量巡检' }}</button><div v-if="quality.analyzing" class="analysis-progress"><span /></div>
      </div><div class="mode-note"><AppIcon name="info" :size="16" /><div><strong>{{ llmNoteTitle }}</strong><span>{{ llmNoteText }}</span></div></div></section>
      <div class="result-column">
        <AppState v-if="!result && !quality.analyzing" title="等待一次质量巡检" description="右侧结果会完整展示缺陷、规范依据、AI 工单草稿、整改提醒和执行轨迹。"><template #default><div class="scanner-illustration" aria-hidden="true"><span /><i /><b /></div></template></AppState>
        <AppState v-else-if="quality.analyzing" type="loading" title="五个 Agent 正在协同工作" description="正在识别缺陷、检索规范并生成可人工复核的草稿。" />
        <template v-else-if="result">
          <section class="card result-hero"><DetectionPreview :image-url="displayImage" :hazards="result.defects" :show-boxes="showAnnotated" alt="质量巡检图片"><div class="visual-toggle"><button type="button" :class="{ active: !showAnnotated }" @click="showAnnotated = false">原图</button><button type="button" :class="{ active: showAnnotated }" @click="showAnnotated = true">检测图</button></div><span class="status-pill dark visual-label">{{ result.is_simulated ? 'AI 模拟结果' : '真实模型结果' }}</span></DetectionPreview><div class="result-summary"><span :class="`risk-badge ${result.risk_level}`"><i class="risk-dot" />{{ riskLabel(result.risk_level) }}</span><h2>{{ result.defects.length ? `发现 ${result.defects.length} 项质量缺陷` : '本次未发现新增缺陷' }}</h2><p class="page-description">{{ result.report_preview }}</p><div class="result-meta"><div><small>任务编号</small><strong class="mono">{{ result.task_id }}</strong></div><div><small>巡检部位</small><strong>{{ result.location }}</strong></div></div></div></section>
          <div class="review-banner"><AppIcon name="info" :size="17" /><span><strong>需要人工复核：</strong>AI 结果仅作为辅助建议，置信度不等于质量合格判定；正式整改工单必须由质检员确认后创建。</span></div>
          <div class="analysis-grid"><section class="card"><div class="card-head"><div><p class="section-kicker">DETECTIONS</p><h3>识别到的缺陷</h3></div><span>{{ yoloDefects.length }} 项</span></div><div v-if="yoloDefects.length" class="form-grid"><article v-for="defect in yoloDefects" :key="defect.id" class="hazard-card" :class="{ 'is-major': defect.is_major }"><div class="hazard-head"><strong>{{ defect.hazard_name }}</strong><span class="hazard-badges"><span v-if="defect.source" class="source-tag" :class="defect.source">{{ sourceLabel(defect.source) }}</span><span v-if="defect.is_major" class="major-tag"><AppIcon name="shield" :size="11" />重大</span><span :class="`risk-badge ${defect.risk_level}`"><i class="risk-dot" />{{ riskLabel(defect.risk_level) }}</span></span></div><p>{{ defect.description }}</p><div v-if="defect.regulation" class="hazard-detail"><AppIcon name="book" :size="13" /><span><b>规范依据</b>{{ defect.regulation }}</span></div><div v-if="defect.suggestion" class="hazard-detail"><AppIcon name="spark" :size="13" /><span><b>整改建议</b>{{ defect.suggestion }}</span></div><div v-if="defect.is_major" class="major-banner"><AppIcon name="shield" :size="14" /><span><b>重大质量缺陷</b>{{ defect.major_basis || '符合重大质量缺陷判定情形' }}</span></div><div class="confidence">识别置信度 {{ confidence(defect.confidence) }}<div class="confidence-bar"><span :style="{ width: `${defect.confidence * 100}%` }" /></div></div></article></div><AppState v-else title="该部位状态正常" description="未识别到可生成整改任务的新增质量缺陷。" /></section><section class="card"><div class="card-head"><div><p class="section-kicker">EVIDENCE</p><h3>规范依据</h3></div><span>{{ result.evidence.length }} 条</span></div><div v-if="result.evidence.length" class="evidence-list"><article v-for="item in result.evidence" :key="item.id || item.article" class="evidence-item"><strong>{{ item.source }}</strong><small>{{ item.article }} · 匹配 {{ item.score ?? 0 }}</small><p>{{ item.content }}</p></article></div><AppState v-else title="暂无足够依据" description="工单会标记为依据待人工补充，不会编造条款。" /></section></div>
          <section v-if="visionLlmHasStatus" class="card llm-card"><div class="card-head"><div><p class="section-kicker">VISION LLM</p><h3>LLM 深度缺陷分析</h3></div><span class="status-pill" :class="visionLlmEnabled ? 'dark' : 'warning'">{{ visionLlmEnabled ? `已启用 · ${visionLlmProviderLabel}` : '未启用 · 纯 YOLO' }}</span></div><template v-if="visionLlmEnabled"><div v-if="visionLlmDefects.length" class="llm-hazard-list"><article v-for="defect in visionLlmDefects" :key="defect.id" class="llm-hazard-card" :class="{ 'is-major': defect.is_major }"><div class="llm-hazard-head"><span class="llm-category mono">{{ defect.hazard_type.toUpperCase() }}</span><strong>{{ defect.hazard_name }}</strong><span :class="`risk-badge ${defect.risk_level}`"><i class="risk-dot" />{{ riskLabel(defect.risk_level) }}</span></div><p>{{ defect.description }}</p><div v-if="defect.regulation" class="hazard-detail"><AppIcon name="book" :size="13" /><span><b>规范依据</b>{{ defect.regulation }}</span></div><div v-if="defect.suggestion" class="hazard-detail"><AppIcon name="spark" :size="13" /><span><b>整改建议</b>{{ defect.suggestion }}</span></div><div v-if="defect.is_major" class="major-banner"><AppIcon name="shield" :size="14" /><span><b>重大质量缺陷</b>{{ defect.major_basis || '符合重大质量缺陷判定情形' }}</span></div></article></div><AppState v-else title="LLM 未发现深层缺陷" description="本次图像经 LLM 复核，未输出可确认的 D1-D5 新增缺陷。" /></template><AppState v-else title="LLM 深度分析未启用" description="未配置 Vision LLM 或调用失败，当前为纯 YOLO 检测；在 backend/.env 配置 VISION_LLM_PROVIDER 后自动启用。" /></section>
          <section v-if="result.work_order_draft" class="card draft-card"><div class="card-head"><div><p class="section-kicker">WORK ORDER DRAFT</p><h3>整改工单草稿</h3></div><span class="status-pill warning">{{ confirmedOrderId ? '已人工确认' : '待人工确认' }}</span></div><p class="page-description">{{ result.work_order_draft.title }} · {{ result.work_order_draft.problem_description }}</p><div class="draft-grid"><div><small>整改位置</small><strong>{{ result.work_order_draft.location }}</strong></div><div><small>建议截止</small><strong>{{ formatDateTime(result.work_order_draft.deadline) }}</strong></div><div><small>责任角色</small><strong>{{ result.work_order_draft.assignee_role }}</strong></div><div><small>来源任务</small><strong class="mono">{{ result.work_order_draft.task_id }}</strong></div></div><div class="two-fields" style="margin-top: 17px"><div><p class="helper-text" style="margin-bottom: 7px">整改要求</p><ul class="clean-list"><li v-for="item in result.work_order_draft.rectification_requirements" :key="item"><AppIcon name="check" :size="14" />{{ item }}</li></ul></div><div><p class="helper-text" style="margin-bottom: 7px">复查要求</p><ul class="clean-list"><li v-for="item in result.work_order_draft.review_requirements" :key="item"><AppIcon name="check" :size="14" />{{ item }}</li></ul></div></div><button class="primary-button button-block" type="button" :disabled="confirming || Boolean(confirmedOrderId)" style="margin-top: 18px" @click="confirmOrder"><AppIcon :name="confirmedOrderId ? 'check' : 'clipboard'" :size="16" />{{ confirmedOrderId ? `已创建工单 ${confirmedOrderId}` : confirming ? '正在创建正式工单…' : '确认创建正式工单' }}</button></section>
          <section class="card"><div class="card-head"><div><p class="section-kicker">WORKER CARE</p><h3>整改工友提醒</h3></div><span class="status-pill dark" style="background: var(--navy-900)">模板回答</span></div><p class="worker-message">{{ result.worker_message || '本次没有需要发送的整改提醒。' }}</p></section>
          <section class="card"><div class="card-head"><div><p class="section-kicker">AGENT TRACE</p><h3>五节点执行轨迹</h3></div><span class="mono">review_required=true</span></div><div class="trace-list"><div v-for="(item, index) in result.agent_trace" :key="`${item.agent}-${index}`" class="trace-item" :class="item.status"><span class="trace-node">{{ String(index + 1).padStart(2, '0') }}</span><div><strong>{{ item.agent }}</strong><small>{{ item.message }}</small></div><span class="trace-time">{{ item.duration_ms ? `${item.duration_ms}ms` : item.status }}</span></div></div></section>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sample-row { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
.sample-card { display: grid; gap: 4px; border: 1px solid var(--line); border-radius: 9px; padding: 6px; background: #fff; text-align: left; cursor: pointer; transition: border-color var(--ease), transform var(--ease); }
.sample-card:hover { border-color: var(--blue); transform: translateY(-1px); }
.sample-card img { width: 100%; height: 62px; border-radius: 6px; object-fit: cover; }
.sample-name { font-size: 10px; font-weight: 700; color: var(--text); }
.sample-hint { color: var(--muted); font-size: 9px; line-height: 1.3; }
.hazard-badges { display: inline-flex; flex-wrap: wrap; justify-content: flex-end; gap: 5px; }
.source-tag { display: inline-flex; align-items: center; min-height: 20px; border-radius: 999px; padding: 0 8px; font-size: 9px; font-weight: 800; }
.source-tag.yolo { color: #2c6fda; background: #eaf2ff; }
.source-tag.llm { color: #7c3aed; background: #f3e8ff; }
.major-tag { display: inline-flex; align-items: center; gap: 3px; min-height: 20px; border-radius: 999px; padding: 0 8px; color: #fff; background: var(--danger); font-size: 9px; font-weight: 800; }
.hazard-card.is-major { border-color: var(--danger); box-shadow: 0 0 0 1px var(--danger); background: #fff7f7; }
.hazard-detail { display: flex; align-items: flex-start; gap: 7px; margin-top: 9px; color: var(--text-soft); font-size: 11px; line-height: 1.55; }
.hazard-detail .app-icon { flex: none; margin-top: 1px; color: var(--blue); }
.hazard-detail b { margin-right: 5px; color: var(--text); font-weight: 800; }
.major-banner { display: flex; align-items: flex-start; gap: 7px; margin-top: 10px; border: 1px solid #f0c4c6; border-radius: 8px; padding: 8px 10px; color: #a13237; background: #fdecec; font-size: 11px; line-height: 1.5; }
.major-banner .app-icon { flex: none; margin-top: 1px; color: var(--danger); }
.major-banner b { margin-right: 5px; font-weight: 800; }
.llm-card { border-color: #e3d5fb; background: linear-gradient(145deg, #fbf8ff, #f5efff); }
.llm-hazard-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; }
.llm-hazard-card { border: 1px solid #e8dcfb; border-radius: 10px; padding: 14px; background: #fff; }
.llm-hazard-card.is-major { border-color: var(--danger); box-shadow: 0 0 0 1px var(--danger); }
.llm-hazard-head { display: flex; align-items: center; flex-wrap: wrap; gap: 9px; }
.llm-hazard-head strong { font-size: 13px; }
.llm-category { display: grid; width: 34px; height: 26px; place-items: center; border-radius: 7px; color: #fff; background: #8b5cf6; font-size: 10px; font-weight: 800; }
.llm-hazard-card p { margin-top: 9px; color: var(--text-soft); font-size: 12px; line-height: 1.6; }
</style>
