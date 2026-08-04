<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import { getApiError } from '@/api/http'
import { workOrdersApi } from '@/api/workOrders'
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageHeader from '@/components/common/AppPageHeader.vue'
import AppState from '@/components/common/AppState.vue'
import { useProjectStore } from '@/stores/project'
import type { WorkOrder } from '@/types/workOrder'
import { formatDateTime } from '@/utils/date'
import { riskLabel, statusLabel } from '@/utils/risk'

const projects = useProjectStore()
const orders = ref<WorkOrder[]>([])
const loading = ref(false)
const error = ref('')
const status = ref('')
const risk = ref('')
const assignee = ref('')
const deadlineFrom = ref('')
const deadlineTo = ref('')
const query = ref('')

async function load(): Promise<void> {
  if (!projects.currentProject?.id) return
  loading.value = true
  error.value = ''
  try { orders.value = await workOrdersApi.list({ project_id: projects.currentProject.id, status: status.value || undefined, risk_level: risk.value || undefined, assignee_user_id: assignee.value.trim() || undefined, deadline_from: deadlineFrom.value ? `${deadlineFrom.value}T00:00:00Z` : undefined, deadline_to: deadlineTo.value ? `${deadlineTo.value}T23:59:59Z` : undefined }) } catch (cause) { error.value = getApiError(cause) } finally { loading.value = false }
}
function filteredOrders(): WorkOrder[] { return orders.value.filter((order) => !query.value || `${order.id} ${order.title} ${order.location}`.toLowerCase().includes(query.value.toLowerCase())) }
onMounted(async () => { if (!projects.projects.length) await projects.loadProjects(); await load() })
watch([() => projects.currentProjectId, status, risk, assignee, deadlineFrom, deadlineTo], load)
</script>

<template>
  <div><AppPageHeader eyebrow="RECTIFICATION WORK ORDERS" title="整改工单" description="所有 AI 工单都必须先人工确认，再进入待整改、整改中、待复查和已关闭状态。"><template #actions><RouterLink class="primary-button" to="/safety/analyze"><AppIcon name="plus" :size="16" />从分析创建工单</RouterLink></template></AppPageHeader><section class="card"><div class="table-toolbar"><div><p class="section-kicker">ACTION QUEUE</p><h3>当前项目工单</h3></div><div class="toolbar-filters"><label class="search-field"><AppIcon name="search" :size="15" /><input v-model.trim="query" placeholder="搜索编号、标题或位置" /></label><select v-model="status" aria-label="筛选工单状态"><option value="">全部状态</option><option value="pending">待整改</option><option value="in_progress">整改中</option><option value="pending_review">待复查</option><option value="closed">已关闭</option></select><select v-model="risk" aria-label="筛选风险等级"><option value="">全部风险</option><option value="critical">重大风险</option><option value="high">高风险</option><option value="medium">中风险</option><option value="low">低风险</option></select><input v-model.trim="assignee" aria-label="按责任人筛选" placeholder="责任人 ID" /><label class="date-filter"><span>截止起</span><input v-model="deadlineFrom" aria-label="截止日期起" type="date" /></label><label class="date-filter"><span>截止止</span><input v-model="deadlineTo" aria-label="截止日期止" type="date" /></label></div></div><div v-if="error" class="alert alert-error" role="alert">{{ error }}</div><AppState v-if="loading" type="loading" title="正在读取工单" /><AppState v-else-if="!filteredOrders().length" title="暂无匹配工单" description="完成安全分析并人工确认工单草稿后，任务会出现在这里。" /><div v-else class="table-wrap"><table class="data-table"><thead><tr><th>编号 / 标题</th><th>位置</th><th>风险</th><th>责任人</th><th>截止时间</th><th>状态</th><th /></tr></thead><tbody><tr v-for="order in filteredOrders()" :key="order.id"><td><strong class="mono">{{ order.id }}</strong><small>{{ order.title }}</small></td><td>{{ order.location }}</td><td><span :class="`risk-badge ${order.risk_level}`"><i class="risk-dot" />{{ riskLabel(order.risk_level) }}</span></td><td class="mono">{{ order.assignee_user_id }}</td><td><strong>{{ formatDateTime(order.deadline) }}</strong><small v-if="order.closed_at">关闭于 {{ formatDateTime(order.closed_at) }}</small></td><td><span :class="`status-pill ${order.status === 'closed' ? 'success' : order.status === 'pending_review' ? 'warning' : ''}`">{{ statusLabel(order.status) }}</span></td><td class="action-cell"><RouterLink class="button-icon" :to="`/work-orders/${order.id}`">详情 <AppIcon name="chevron" :size="13" /></RouterLink></td></tr></tbody></table></div></section></div>
</template>
