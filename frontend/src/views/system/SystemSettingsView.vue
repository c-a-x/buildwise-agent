<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { getApiError } from '@/api/http'
import { systemApi, type RuntimeStatus } from '@/api/system'
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageHeader from '@/components/common/AppPageHeader.vue'

const runtime = ref<RuntimeStatus | null>(null)
const error = ref('')
const databaseLabel = computed(() => {
  if (!runtime.value) return '读取中…'
  const name = runtime.value.database.dialect === 'sqlite' ? 'SQLite' : runtime.value.database.dialect
  return `${name} · ${runtime.value.database.status === 'connected' ? '已连接' : '不可用'}`
})

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
    <AppPageHeader eyebrow="SYSTEM SETTINGS" title="系统设置" description="查看当前本地运行模式和后续可配置项。" />
    <div v-if="error" class="alert alert-error" role="alert">{{ error }}</div>
    <div class="placeholder-grid">
      <section class="card">
        <div class="card-head"><div><p class="section-kicker">RUNTIME</p><h3>运行配置</h3></div><span :class="`status-pill ${runtime?.database.status === 'connected' ? 'success' : 'warning'}`">{{ runtime ? (runtime.database.status === 'connected' ? '数据库在线' : '数据库异常') : '读取中…' }}</span></div>
        <div class="detail-line"><span>视觉 Provider</span><strong class="mono">{{ runtime?.providers.vision || '读取中…' }}</strong></div>
        <div class="detail-line"><span>检索 Provider</span><strong class="mono">{{ runtime?.providers.retrieval || '读取中…' }}</strong></div>
        <div class="detail-line"><span>文本 Provider</span><strong class="mono">{{ runtime?.providers.text || '读取中…' }}</strong></div>
        <div class="detail-line"><span>数据存储</span><strong class="mono">{{ databaseLabel }}</strong></div>
      </section>
      <section class="card"><div class="card-head"><div><p class="section-kicker">SAFETY BOUNDARY</p><h3>安全边界</h3></div><AppIcon name="lock" :size="17" /></div><ul class="clean-list"><li><AppIcon name="check" :size="15" />所有模拟结果显式标记 is_simulated=true</li><li><AppIcon name="check" :size="15" />所有 AI 结论显式标记 review_required=true</li><li><AppIcon name="check" :size="15" />Agent 只生成草稿，不自动创建正式工单</li><li><AppIcon name="check" :size="15" />日报数字来自数据库 SQL 统计</li></ul></section>
    </div>
    <section class="card endpoint-card"><div class="card-head"><div><p class="section-kicker">NEXT CONFIGURATION</p><h3>后续接入项</h3></div><span>管理员可见</span></div><div class="endpoint-row"><span class="status-dot muted" />真实 YOLO / Ultralytics 视觉 Provider</div><div class="endpoint-row"><span class="status-dot muted" />Chroma 向量检索与规范文档重建</div><div class="endpoint-row"><span class="status-dot muted" />OpenAI 兼容文本 Provider 与结构化输出</div></section>
  </div>
</template>
