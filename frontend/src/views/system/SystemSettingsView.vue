<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { getApiError } from '@/api/http'
import { systemApi, type CapabilityStatus, type ProviderCapability, type RuntimeStatus } from '@/api/system'
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageHeader from '@/components/common/AppPageHeader.vue'

const runtime = ref<RuntimeStatus | null>(null)
const error = ref('')
const databaseLabel = computed(() => {
  if (!runtime.value) return '读取中…'
  const name = runtime.value.database.dialect === 'sqlite' ? 'SQLite' : runtime.value.database.dialect
  return `${name} · ${runtime.value.database.status === 'connected' ? '已连接' : '不可用'}`
})
const capabilities = computed<ProviderCapability[]>(() => Object.values(runtime.value?.capabilities ?? {}).filter((capability): capability is ProviderCapability => capability !== undefined))
const STATUS_LABELS: Record<CapabilityStatus, string> = {
  available: '可用',
  configured: '已配置（待验证）',
  simulated: '离线模拟',
  not_configured: '未配置',
  unavailable: '不可用',
}
const STATUS_CLASSES: Record<CapabilityStatus, string> = {
  available: 'success',
  configured: 'warning',
  simulated: 'simulated',
  not_configured: 'warning',
  unavailable: 'danger',
}
const statusLabel = (status: CapabilityStatus): string => STATUS_LABELS[status]
const statusClass = (status: CapabilityStatus): string => STATUS_CLASSES[status]

async function loadRuntime(): Promise<void> {
  try {
    runtime.value = await systemApi.health()
  } catch (cause) {
    error.value = getApiError(cause)
  }
}

onMounted(() => { void loadRuntime() })
</script>

<template>
  <div>
    <AppPageHeader eyebrow="SYSTEM SETTINGS" title="系统设置" description="查看 Provider 的真实就绪状态、离线降级路径和数据库持久化状态。" />
    <div v-if="error" class="alert alert-error" role="alert">{{ error }}</div>
    <div class="placeholder-grid">
      <section class="card">
        <div class="card-head"><div><p class="section-kicker">RUNTIME</p><h3>运行配置</h3></div><span :class="`status-pill ${runtime?.database.status === 'connected' ? 'success' : 'warning'}`">{{ runtime ? (runtime.database.status === 'connected' ? '数据库在线' : '数据库异常') : '读取中…' }}</span></div>
        <div class="detail-line"><span>视觉 Provider</span><strong class="mono">{{ runtime?.providers.vision || '读取中…' }}</strong></div>
        <div class="detail-line"><span>检索 Provider</span><strong class="mono">{{ runtime?.providers.retrieval || '读取中…' }}</strong></div>
        <div class="detail-line"><span>文本 Provider</span><strong class="mono">{{ runtime?.providers.text || '读取中…' }}</strong></div>
        <div class="detail-line"><span>数据存储</span><strong class="mono">{{ databaseLabel }}</strong></div>
        <div class="detail-line"><span>持久化</span><strong>{{ runtime?.database.persistent ? '真实文件/服务' : '临时内存' }}</strong></div>
      </section>
      <section class="card"><div class="card-head"><div><p class="section-kicker">SAFETY BOUNDARY</p><h3>安全边界</h3></div><AppIcon name="lock" :size="17" /></div><ul class="clean-list"><li><AppIcon name="check" :size="15" />所有模拟结果显式标记 is_simulated=true</li><li><AppIcon name="check" :size="15" />所有 AI 结论显式标记 review_required=true</li><li><AppIcon name="check" :size="15" />Agent 只生成草稿，不自动创建正式工单</li><li><AppIcon name="check" :size="15" />日报数字来自数据库 SQL 统计</li></ul></section>
    </div>
    <section class="card capability-panel">
      <div class="card-head"><div><p class="section-kicker">PROVIDER CAPABILITIES</p><h3>能力状态</h3></div><span>{{ capabilities.length }} 项只读预检</span></div>
      <div v-if="capabilities.length" class="capability-grid">
        <article v-for="capability in capabilities" :key="capability.key" class="capability-card">
          <div class="capability-head">
            <div><strong>{{ capability.name }}</strong><small class="mono">{{ capability.provider }}</small></div>
            <span :class="`status-pill ${statusClass(capability.status)}`">{{ statusLabel(capability.status) }}</span>
          </div>
          <p>{{ capability.reason }}</p>
          <div class="capability-next"><span>下一步</span>{{ capability.next_step }}</div>
        </article>
      </div>
      <p v-else class="muted-copy">当前后端版本未返回能力详情；基础 Provider 与数据库状态仍可用。</p>
    </section>
  </div>
</template>
