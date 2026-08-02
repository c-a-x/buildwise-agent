<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getApiError } from '@/api/http'
import { workOrdersApi } from '@/api/workOrders'
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageHeader from '@/components/common/AppPageHeader.vue'
import AppState from '@/components/common/AppState.vue'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import type { WorkOrderStatus } from '@/types/api'
import type { WorkOrder } from '@/types/workOrder'
import { formatDateTime } from '@/utils/date'
import { riskLabel, statusLabel } from '@/utils/risk'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const app = useAppStore()
const order = ref<WorkOrder | null>(null)
const loading = ref(false)
const error = ref('')
const note = ref('')
const selectedStatus = ref<WorkOrderStatus | ''>('')
const saving = ref(false)
const transitionMap: Record<WorkOrderStatus, WorkOrderStatus[]> = { pending: ['in_progress'], in_progress: ['pending_review'], pending_review: ['in_progress', 'closed'], closed: [] }
const canMutate = computed(() => ['admin', 'project_manager', 'safety_officer'].includes(auth.user?.role || ''))
const availableStatuses = computed(() => order.value ? transitionMap[order.value.status] : [])

async function load(): Promise<void> {
  const id = String(route.params.id)
  if (!id) return
  loading.value = true
  error.value = ''
  try { order.value = await workOrdersApi.get(id) } catch (cause) { error.value = getApiError(cause) } finally { loading.value = false }
}
async function updateStatus(): Promise<void> {
  if (!order.value || !selectedStatus.value) return
  if (selectedStatus.value === 'closed' && !note.value.trim()) { error.value = '关闭工单前请填写复查备注'; return }
  saving.value = true
  error.value = ''
  try { order.value = await workOrdersApi.updateStatus(order.value.id, selectedStatus.value, note.value); selectedStatus.value = ''; note.value = ''; app.showNotice('工单状态已更新') } catch (cause) { error.value = getApiError(cause) } finally { saving.value = false }
}
onMounted(load)
watch(() => route.params.id, load)
</script>

<template>
  <div><AppPageHeader eyebrow="WORK ORDER DETAIL" title="工单详情" description="查看来源隐患、整改要求和每一次状态变更。"><template #actions><button class="secondary-button" type="button" @click="router.back"><AppIcon name="arrow" :size="15" style="transform: rotate(180deg)" />返回列表</button></template></AppPageHeader><AppState v-if="loading" type="loading" title="正在读取工单详情" /><AppState v-else-if="error && !order" type="error" :description="error"><RouterLink class="secondary-button" to="/work-orders">返回工单列表</RouterLink></AppState><template v-else-if="order"><div v-if="error" class="alert alert-error" role="alert">{{ error }}</div><section class="card detail-hero"><div><span :class="`risk-badge ${order.risk_level}`"><i class="risk-dot" />{{ riskLabel(order.risk_level) }}</span><h2>{{ order.title }}</h2><p>{{ order.problem_description }}</p></div><div class="detail-hero-meta"><span :class="`status-pill ${order.status === 'closed' ? 'success' : order.status === 'pending_review' ? 'warning' : ''}`">{{ statusLabel(order.status) }}</span><small class="mono">{{ order.id }}</small></div></section><div class="detail-grid"><div class="detail-main"><section class="card"><div class="card-head"><div><p class="section-kicker">RECTIFICATION PLAN</p><h3>整改与复查要求</h3></div><span>{{ order.ai_generated ? 'AI 草稿已确认' : '人工创建' }}</span></div><div class="two-fields"><div><p class="helper-text" style="margin-bottom: 9px">整改要求</p><ul class="clean-list"><li v-for="item in order.rectification_requirements" :key="item"><AppIcon name="check" :size="15" />{{ item }}</li></ul></div><div><p class="helper-text" style="margin-bottom: 9px">复查要求</p><ul class="clean-list"><li v-for="item in order.review_requirements" :key="item"><AppIcon name="check" :size="15" />{{ item }}</li></ul></div></div><div class="worker-note"><AppIcon name="worker" :size="17" /><div><strong>工友提醒</strong><p>{{ order.worker_message }}</p></div></div></section><section class="card"><div class="card-head"><div><p class="section-kicker">STATUS TIMELINE</p><h3>状态时间线</h3></div><span>{{ order.events.length }} 个事件</span></div><div class="trace-list"><div v-for="event in order.events" :key="event.id" class="trace-item"><span class="trace-node"><AppIcon :name="event.event_type === 'created' ? 'plus' : 'check'" :size="13" /></span><div><strong>{{ event.event_type === 'created' ? '工单创建' : `${statusLabel(event.from_status || '')} → ${statusLabel(event.to_status || '')}` }}</strong><small>{{ event.note || '系统记录状态变更' }} · {{ event.actor_user_id }}</small></div><span class="trace-time">{{ formatDateTime(event.created_at) }}</span></div></div></section></div><aside class="detail-side"><section class="card"><div class="card-head"><h3>工单信息</h3><span>基础字段</span></div><div class="detail-line"><span>施工位置</span><strong>{{ order.location }}</strong></div><div class="detail-line"><span>责任人</span><strong class="mono">{{ order.assignee_user_id }}</strong></div><div class="detail-line"><span>截止时间</span><strong>{{ formatDateTime(order.deadline) }}</strong></div><div class="detail-line"><span>来源任务</span><strong class="mono">{{ order.source_task_id }}</strong></div><div class="detail-line"><span>创建时间</span><strong>{{ formatDateTime(order.created_at) }}</strong></div></section><section class="card"><div class="card-head"><h3>状态变更</h3><span>需有权限</span></div><div v-if="canMutate && availableStatuses.length" class="form-grid"><div class="form-field"><label for="next-status">下一状态</label><select id="next-status" v-model="selectedStatus"><option value="">请选择</option><option v-for="value in availableStatuses" :key="value" :value="value">{{ statusLabel(value) }}</option></select></div><div class="form-field"><label for="status-note">备注 <span v-if="selectedStatus === 'closed'">*</span></label><textarea id="status-note" v-model.trim="note" placeholder="记录整改或复查结论" /></div><button class="primary-button button-block" type="button" :disabled="saving || !selectedStatus" @click="updateStatus">{{ saving ? '保存中…' : '保存状态变更' }}</button></div><div v-else class="state-card" style="min-height: 130px"><strong>{{ order.status === 'closed' ? '工单已关闭' : '当前角色不可变更状态' }}</strong><p>{{ order.status === 'closed' ? '该工单已完成闭环。' : '请由安全员或项目经理处理下一步。' }}</p></div></section><section class="card attachment-card"><div class="card-head"><h3>整改附件</h3><span>可选控件</span></div><label class="secondary-button button-block"><AppIcon name="upload" :size="15" />上传整改图片<input type="file" accept="image/*" hidden /></label><p class="helper-text">MVP 保留控件和接口，正式归档能力将在后续版本启用。</p></section></aside></div></template>
  </div>
</template>
