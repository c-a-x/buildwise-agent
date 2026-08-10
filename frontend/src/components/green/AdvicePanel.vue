<script setup lang="ts">
import { getApiError } from '@/api/http'
import AppIcon from '@/components/common/AppIcon.vue'
import { useGreenStore } from '@/stores/green'

const props = defineProps<{
  sourceType: 'carbon' | 'assessment'
  analysisId?: string | null
  assessmentId?: string | null
}>()

const green = useGreenStore()

const projectId = (): string | null => green.currentResult?.project_id ?? green.currentAssessment?.project_id ?? null
const matchesSource = (): boolean => green.advice?.source_type === props.sourceType

async function generate(): Promise<void> {
  const pid = projectId()
  if (!pid) return
  try {
    await green.generateAdvice({
      project_id: pid,
      source_type: props.sourceType,
      analysis_id: props.analysisId ?? null,
      assessment_id: props.assessmentId ?? null,
    })
  } catch (cause) {
    // 错误由 store 的 adviceError 呈现
    getApiError(cause)
  }
}
</script>

<template>
  <section class="card advice-card">
    <div class="card-head">
      <div><p class="section-kicker">AI OPTIMIZATION</p><h3>AI 优化建议</h3></div>
      <button type="button" class="secondary-button" :disabled="green.generatingAdvice" @click="generate">
        <AppIcon name="spark" :size="16" />{{ green.generatingAdvice ? '生成中…' : '生成 AI 优化建议' }}
      </button>
    </div>
    <p v-if="green.adviceError" class="error-text">{{ green.adviceError }}</p>
    <div v-if="green.generatingAdvice" class="loading-dots">正在生成绿色施工优化建议</div>
    <template v-else-if="green.advice && matchesSource()">
      <p class="advice-text">{{ green.advice.advice }}</p>
      <div class="advice-meta">
        <span class="status-pill" :class="green.advice.is_simulated ? 'warning' : 'success'">{{ green.advice.is_simulated ? '演示建议' : 'AI 生成' }}</span>
      </div>
    </template>
    <p v-else class="muted-copy">点击「生成 AI 优化建议」，由大模型基于当前核算/评估结果给出可执行的绿色施工行动建议。</p>
  </section>
</template>

<style scoped>
.advice-card { margin-top: 12px; }
.advice-text { margin: 0 0 10px; white-space: pre-wrap; color: var(--text); font-size: 13px; line-height: 1.8; }
.advice-meta { display: flex; gap: 8px; }
</style>
