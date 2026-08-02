<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { getApiError } from '@/api/http'
import { workOrdersApi } from '@/api/workOrders'
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageHeader from '@/components/common/AppPageHeader.vue'
import AppState from '@/components/common/AppState.vue'
import { useAppStore } from '@/stores/app'
import { useProjectStore } from '@/stores/project'
import { useSafetyStore } from '@/stores/safety'
import { formatDateTime } from '@/utils/date'
import { riskLabel } from '@/utils/risk'

const projects = useProjectStore()
const safety = useSafetyStore()
const app = useAppStore()
const file = ref<File | null>(null)
const previewUrl = ref('')
const showAnnotated = ref(false)
const location = ref('B1 北侧临边')
const workType = ref('主体结构')
const description = ref('')
const demoScenario = ref('no_helmet')
const localError = ref('')
const confirming = ref(false)
const confirmedOrderId = ref('')
const result = computed(() => safety.currentResult)
const assetBase = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace(/\/api\/v1\/?$/, '')
const displayImage = computed(() => {
  if (showAnnotated.value && result.value?.annotated_url) return `${assetBase}${result.value.annotated_url}`
  if (previewUrl.value) return previewUrl.value
  return result.value ? `${assetBase}${result.value.file_url}` : ''
})

function selectProject(event: Event): void {
  projects.selectProject((event.target as HTMLSelectElement).value)
}

onMounted(() => { if (!projects.projects.length) void projects.loadProjects() })

function handleFile(event: Event): void {
  const selected = (event.target as HTMLInputElement).files?.[0]
  if (!selected) return
  file.value = selected
  previewUrl.value = URL.createObjectURL(selected)
  safety.clearResult()
  confirmedOrderId.value = ''
}

async function analyze(): Promise<void> {
  localError.value = ''
  if (!file.value) { localError.value = '请先选择一张现场图片'; return }
  if (!projects.currentProject?.id) { localError.value = '当前没有可用项目'; return }
  try {
    await safety.analyze(file.value, { project_id: projects.currentProject.id, location: location.value, work_type: workType.value, description: description.value, demo_scenario: demoScenario.value })
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
  <div><AppPageHeader eyebrow="SAFETY INTELLIGENCE" title="现场安全分析" description="上传施工现场图片，让五个离线 Agent 协同完成识别、检索、任务和日报预览。"><template #actions><span class="status-pill dark"><span class="status-dot online" />Mock Provider 在线</span></template></AppPageHeader>
    <div class="safety-layout">
      <section class="card input-panel"><div class="card-head"><div><p class="section-kicker">01 · INPUT</p><h3>准备一次现场分析</h3></div><span class="mono">120s timeout</span></div><div class="form-grid">
        <div class="form-field"><label>当前项目</label><select :value="projects.currentProject?.id" @change="selectProject"><option v-for="project in projects.projects" :key="project.id" :value="project.id">{{ project.name }}</option></select></div>
        <div class="form-field"><label>现场图片 <span>*</span></label><label class="upload-zone"><input type="file" accept="image/jpeg,image/png,image/webp" @change="handleFile" /><img v-if="previewUrl" :src="previewUrl" alt="已选择的现场图片预览" /><span v-else class="upload-icon"><AppIcon name="upload" :size="22" /></span><strong>{{ file ? '重新选择现场图片' : '点击或拖拽上传现场图片' }}</strong><small>JPEG / PNG / WEBP · 最大 10 MB</small><span v-if="file" class="file-name">{{ file.name }}</span></label></div>
        <div class="two-fields"><div class="form-field"><label for="location">施工位置</label><input id="location" v-model.trim="location" placeholder="如：B1 北侧临边" /></div><div class="form-field"><label for="work-type">作业类型</label><input id="work-type" v-model.trim="workType" placeholder="如：主体结构" /></div></div>
        <div class="form-field"><label for="description">现场说明 <span>可选</span></label><textarea id="description" v-model.trim="description" placeholder="补充光线、作业环境或需要重点关注的信息" /></div>
        <div class="form-field"><label for="demo-scenario">演示场景</label><select id="demo-scenario" v-model="demoScenario"><option value="no_helmet">未戴安全帽 · 高风险</option><option value="missing_guardrail">临边防护缺失 · 重大风险</option><option value="no_safety_vest">未穿安全背心 · 中风险</option><option value="normal">正常现场 · 无新增隐患</option></select><p class="helper-text">仅用于离线演示，结果会显式标记为模拟并需要人工复核。</p></div>
        <div v-if="localError || safety.error" class="alert alert-error" role="alert">{{ localError || safety.error }}</div>
        <button class="primary-button analyze-button button-block" type="button" :disabled="safety.analyzing" @click="analyze"><AppIcon :name="safety.analyzing ? 'refresh' : 'spark'" :size="16" />{{ safety.analyzing ? 'Agent 正在协同分析…' : '开始安全分析' }}</button><div v-if="safety.analyzing" class="analysis-progress"><span /></div>
      </div><div class="mode-note"><AppIcon name="info" :size="16" /><div><strong>当前为离线模拟模式</strong><span>SafetyAgent 使用本地规则；RagAgent 使用内置规范条目；不会调用付费模型。</span></div></div></section>
      <div class="result-column">
        <AppState v-if="!result && !safety.analyzing" title="等待一次现场分析" description="右侧结果会完整展示风险、规范依据、AI 工单草稿、工友提醒和执行轨迹。"><template #default><div class="scanner-illustration" aria-hidden="true"><span /><i /><b /></div></template></AppState>
        <AppState v-else-if="safety.analyzing" type="loading" title="五个 Agent 正在协同工作" description="正在识别现场、检索规范并生成可人工复核的草稿。" />
        <template v-else-if="result">
          <section class="card result-hero"><div class="result-visual"><div v-if="displayImage" class="result-image-wrap"><img :src="displayImage" alt="安全分析现场图片" /></div><div v-else class="result-visual-placeholder"><AppIcon name="shield" :size="40" /></div><div class="visual-toggle"><button type="button" :class="{ active: !showAnnotated }" @click="showAnnotated = false">原图</button><button type="button" :class="{ active: showAnnotated }" :disabled="!result.annotated_url" @click="showAnnotated = true">检测图</button></div><span class="status-pill dark visual-label">{{ result.is_simulated ? 'AI 模拟结果' : '真实模型结果' }}</span></div><div class="result-summary"><span :class="`risk-badge ${result.risk_level}`"><i class="risk-dot" />{{ riskLabel(result.risk_level) }}</span><h2>{{ result.hazards.length ? `发现 ${result.hazards.length} 项现场隐患` : '本次未发现新增隐患' }}</h2><p class="page-description">{{ result.report_preview }}</p><div class="result-meta"><div><small>任务编号</small><strong class="mono">{{ result.task_id }}</strong></div><div><small>现场位置</small><strong>{{ result.location }}</strong></div></div></div></section>
          <div class="review-banner"><AppIcon name="info" :size="17" /><span><strong>需要人工复核：</strong>AI 结果仅作为辅助建议，置信度不等于法规符合性；正式工单必须由项目人员确认后创建。</span></div>
          <div class="analysis-grid"><section class="card"><div class="card-head"><div><p class="section-kicker">DETECTIONS</p><h3>识别到的隐患</h3></div><span>{{ result.hazards.length }} 项</span></div><div v-if="result.hazards.length" class="form-grid"><article v-for="hazard in result.hazards" :key="hazard.id" class="hazard-card"><div class="hazard-head"><strong>{{ hazard.hazard_name }}</strong><span :class="`risk-badge ${hazard.risk_level}`"><i class="risk-dot" />{{ riskLabel(hazard.risk_level) }}</span></div><p>{{ hazard.description }}</p><div class="confidence">识别置信度 {{ confidence(hazard.confidence) }}<div class="confidence-bar"><span :style="{ width: `${hazard.confidence * 100}%` }" /></div></div></article></div><AppState v-else title="现场状态正常" description="未识别到可生成整改任务的新增隐患。" /></section><section class="card"><div class="card-head"><div><p class="section-kicker">EVIDENCE</p><h3>规范依据</h3></div><span>{{ result.evidence.length }} 条</span></div><div v-if="result.evidence.length" class="evidence-list"><article v-for="item in result.evidence" :key="item.id || item.article" class="evidence-item"><strong>{{ item.source }}</strong><small>{{ item.article }} · 匹配 {{ item.score ?? 0 }}</small><p>{{ item.content }}</p></article></div><AppState v-else title="暂无足够依据" description="工单会标记为依据待人工补充，不会编造条款。" /></section></div>
          <section v-if="result.work_order_draft" class="card draft-card"><div class="card-head"><div><p class="section-kicker">WORK ORDER DRAFT</p><h3>整改工单草稿</h3></div><span class="status-pill warning">{{ confirmedOrderId ? '已人工确认' : '待人工确认' }}</span></div><p class="page-description">{{ result.work_order_draft.title }} · {{ result.work_order_draft.problem_description }}</p><div class="draft-grid"><div><small>整改位置</small><strong>{{ result.work_order_draft.location }}</strong></div><div><small>建议截止</small><strong>{{ formatDateTime(result.work_order_draft.deadline) }}</strong></div><div><small>责任角色</small><strong>{{ result.work_order_draft.assignee_role }}</strong></div><div><small>来源任务</small><strong class="mono">{{ result.work_order_draft.task_id }}</strong></div></div><div class="two-fields" style="margin-top: 17px"><div><p class="helper-text" style="margin-bottom: 7px">整改要求</p><ul class="clean-list"><li v-for="item in result.work_order_draft.rectification_requirements" :key="item"><AppIcon name="check" :size="14" />{{ item }}</li></ul></div><div><p class="helper-text" style="margin-bottom: 7px">复查要求</p><ul class="clean-list"><li v-for="item in result.work_order_draft.review_requirements" :key="item"><AppIcon name="check" :size="14" />{{ item }}</li></ul></div></div><button class="primary-button button-block" type="button" :disabled="confirming || Boolean(confirmedOrderId)" style="margin-top: 18px" @click="confirmOrder"><AppIcon :name="confirmedOrderId ? 'check' : 'clipboard'" :size="16" />{{ confirmedOrderId ? `已创建工单 ${confirmedOrderId}` : confirming ? '正在创建正式工单…' : '确认创建正式工单' }}</button></section>
          <section class="card"><div class="card-head"><div><p class="section-kicker">WORKER CARE</p><h3>工友安全提醒</h3></div><span class="status-pill dark" style="background: var(--navy-900)">模板回答</span></div><p class="worker-message">{{ result.worker_message || '本次没有需要发送的工友提醒。' }}</p></section>
          <section class="card"><div class="card-head"><div><p class="section-kicker">AGENT TRACE</p><h3>五节点执行轨迹</h3></div><span class="mono">review_required=true</span></div><div class="trace-list"><div v-for="(item, index) in result.agent_trace" :key="`${item.agent}-${index}`" class="trace-item" :class="item.status"><span class="trace-node">{{ String(index + 1).padStart(2, '0') }}</span><div><strong>{{ item.agent }}</strong><small>{{ item.message }}</small></div><span class="trace-time">{{ item.duration_ms ? `${item.duration_ms}ms` : item.status }}</span></div></div></section>
        </template>
      </div>
    </div>
  </div>
</template>
