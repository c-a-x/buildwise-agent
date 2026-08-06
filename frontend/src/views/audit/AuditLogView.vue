<script setup lang="ts">
/** 权限审计：仅 admin 可见的关键操作日志（登录/登出、工单、项目），支持筛选与分页。 */

import { computed, onMounted, ref } from 'vue'

import { auditApi } from '@/api/audit'
import { getApiError } from '@/api/http'
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageHeader from '@/components/common/AppPageHeader.vue'
import AppState from '@/components/common/AppState.vue'
import { formatDateTime } from '@/utils/date'
import type { AuditLogEntry } from '@/types/audit'

const PAGE_SIZE = 20

const ACTION_LABELS: Record<string, string> = {
  user_login: '登录',
  user_logout: '登出',
  create_project: '创建项目',
  confirm_work_order: '确认工单',
  change_work_order_status: '工单状态变更',
  attach_work_order_image: '工单附图',
}

const RESOURCE_LABELS: Record<string, string> = {
  auth: '认证',
  project: '项目',
  work_order: '工单',
}

const RESOURCE_TYPES = ['auth', 'project', 'work_order']

const items = ref<AuditLogEntry[]>([])
const total = ref(0)
const offset = ref(0)
const loading = ref(false)
const localError = ref('')

const actionFilter = ref('')
const resourceTypeFilter = ref('')
const actionOptions = ref<string[]>([])

const currentPage = computed(() => Math.floor(offset.value / PAGE_SIZE) + 1)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

function actionLabel(action: string): string {
  return ACTION_LABELS[action] ?? action
}

function resourceLabel(type: string): string {
  return RESOURCE_LABELS[type] ?? type
}

function detailText(detail: Record<string, unknown> | null): string {
  if (!detail) return '—'
  try {
    return JSON.stringify(detail)
  } catch {
    return '—'
  }
}

function shortDetail(detail: Record<string, unknown> | null): string {
  const text = detailText(detail)
  return text.length > 60 ? `${text.slice(0, 60)}…` : text
}

async function loadLogs(): Promise<void> {
  loading.value = true
  localError.value = ''
  try {
    const params: { action?: string; resource_type?: string; limit: number; offset: number } = { limit: PAGE_SIZE, offset: offset.value }
    if (actionFilter.value) params.action = actionFilter.value
    if (resourceTypeFilter.value) params.resource_type = resourceTypeFilter.value
    const data = await auditApi.logs(params)
    items.value = data.items
    total.value = data.total
  } catch (cause) {
    items.value = []
    total.value = 0
    localError.value = getApiError(cause)
  } finally {
    loading.value = false
  }
}

async function loadActions(): Promise<void> {
  try {
    actionOptions.value = await auditApi.actions()
  } catch {
    actionOptions.value = []
  }
}

function query(): void {
  offset.value = 0
  void loadLogs()
}

function nextPage(): void {
  if (currentPage.value >= totalPages.value) return
  offset.value += PAGE_SIZE
  void loadLogs()
}

function prevPage(): void {
  if (currentPage.value <= 1) return
  offset.value -= PAGE_SIZE
  void loadLogs()
}

async function refresh(): Promise<void> {
  await Promise.all([loadActions(), loadLogs()])
}

onMounted(() => { void refresh() })
</script>

<template>
  <div>
    <AppPageHeader eyebrow="PERMISSION AUDIT" title="权限审计" description="记录登录/登出、工单确认/状态变更/附图与项目创建等关键操作及来源 IP，供追溯与合规留痕。仅管理员可见。" />

    <section class="card filter-card">
      <div class="card-head"><div><p class="section-kicker">FILTER</p><h3>筛选条件</h3></div><span class="mono">共 {{ total }} 条记录</span></div>
      <div class="filter-bar">
        <div class="form-field">
          <label>操作</label>
          <select v-model="actionFilter">
            <option value="">全部操作</option>
            <option v-for="action in actionOptions" :key="action" :value="action">{{ actionLabel(action) }}</option>
          </select>
        </div>
        <div class="form-field">
          <label>资源类型</label>
          <select v-model="resourceTypeFilter">
            <option value="">全部类型</option>
            <option v-for="type in RESOURCE_TYPES" :key="type" :value="type">{{ resourceLabel(type) }}</option>
          </select>
        </div>
        <div class="filter-actions">
          <button type="button" class="primary-button" :disabled="loading" @click="query"><AppIcon name="spark" :size="15" />查询</button>
          <button type="button" class="secondary-button" :disabled="loading" @click="refresh"><AppIcon name="refresh" :size="15" />刷新</button>
        </div>
      </div>
      <p v-if="localError" class="error-text" role="alert">{{ localError }}</p>
    </section>

    <section class="card table-card">
      <div class="card-head"><div><p class="section-kicker">AUDIT LOG</p><h3>审计日志</h3></div><AppIcon name="lock" :size="17" /></div>
      <div v-if="loading" class="table-wrap"><div class="loading-dots">正在加载审计日志</div></div>
      <div v-else-if="localError" class="table-wrap"><AppState type="error" title="审计日志加载失败" :description="localError"><button type="button" class="secondary-button" @click="refresh">重新加载</button></AppState></div>
      <div v-else-if="!items.length" class="table-wrap"><AppState type="empty" title="暂无审计记录" description="登录、登出、项目创建与工单操作后，这里会显示对应的审计条目。" /></div>
      <div v-else class="table-wrap">
        <table class="data-table">
          <thead><tr><th>时间</th><th>操作</th><th>资源类型</th><th>用户</th><th>资源ID</th><th>IP</th><th>详情</th></tr></thead>
          <tbody>
            <tr v-for="entry in items" :key="entry.id">
              <td class="nowrap-cell">{{ formatDateTime(entry.created_at) }}</td>
              <td><span class="status-pill dark">{{ actionLabel(entry.action) }}</span></td>
              <td>{{ resourceLabel(entry.resource_type) }}</td>
              <td><strong>{{ entry.username || entry.user_id }}</strong></td>
              <td><span class="mono id-cell">{{ entry.resource_id || '—' }}</span></td>
              <td><span class="mono">{{ entry.ip_address || '—' }}</span></td>
              <td><span class="detail-cell" :title="detailText(entry.detail_json)">{{ shortDetail(entry.detail_json) }}</span></td>
            </tr>
          </tbody>
        </table>
        <div class="pagination-row">
          <span class="mono">第 {{ currentPage }}/{{ totalPages }} 页</span>
          <div class="pagination-buttons">
            <button type="button" class="button-icon" :disabled="currentPage <= 1 || loading" @click="prevPage">上一页</button>
            <button type="button" class="button-icon" :disabled="currentPage >= totalPages || loading" @click="nextPage">下一页</button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.filter-card { margin-bottom: 18px; }
.filter-bar { display: flex; align-items: flex-end; gap: 14px; flex-wrap: wrap; }
.filter-bar .form-field { min-width: 180px; flex: 1; }
.filter-actions { display: flex; gap: 10px; padding-bottom: 2px; }
.table-card { margin-top: 0; }
.table-wrap { overflow-x: auto; }
.nowrap-cell { white-space: nowrap; }
.id-cell { font-size: 11px; }
.detail-cell { display: inline-block; max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; vertical-align: bottom; color: var(--text-soft); font-size: 11px; }
.pagination-row { display: flex; align-items: center; justify-content: flex-end; gap: 14px; padding-top: 14px; border-top: 1px solid var(--line); margin-top: 14px; }
.pagination-row .mono { color: var(--muted); font-size: 11px; }
.pagination-buttons { display: flex; gap: 8px; }
@media (max-width: 640px) { .filter-bar .form-field { min-width: 100%; } }
</style>
