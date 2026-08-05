<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { getApiError } from '@/api/http'
import { workerCareApi, type WorkerCitation, type WorkerMessage } from '@/api/workerCare'
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageHeader from '@/components/common/AppPageHeader.vue'
import VoiceInput from '@/components/worker-care/VoiceInput.vue'
import { useProjectStore } from '@/stores/project'
import { formatDateTime } from '@/utils/date'

interface ChatLine { mine: boolean; text: string; time: string; source?: string; citations?: WorkerCitation[] }
const projects = useProjectStore()
const question = ref('')
const sending = ref(false)
const error = ref('')
const messages = ref<ChatLine[]>([{ mine: false, text: '你好，我是工友安全助手。可以问我个人防护、临边作业或整改步骤，我会用简短的话说明下一步。', time: new Date().toISOString(), source: '模板回答' }])
const quickQuestions = ['进入现场前要检查什么？', '安全帽应该怎么正确佩戴？', '整改完成后要做什么？']
const projectId = computed(() => projects.currentProject?.id || '')

function sourceLabel(source: string): string {
  if (source === 'rag') return '规范检索'
  if (source === 'template') return '模板回答 · 模拟'
  return source
}

async function send(text = question.value): Promise<void> {
  const trimmed = text.trim()
  if (!trimmed || !projectId.value || sending.value) return
  question.value = ''
  messages.value.push({ mine: true, text: trimmed, time: new Date().toISOString() })
  sending.value = true
  error.value = ''
  try {
    const response: WorkerMessage = await workerCareApi.chat(projectId.value, trimmed)
    messages.value.push({ mine: false, text: response.answer, time: response.created_at, source: sourceLabel(response.answer_source), citations: response.citations })
  } catch (cause) {
    error.value = getApiError(cause)
  } finally {
    sending.value = false
  }
}
function onVoiceText(text: string): void {
  question.value = text
}
onMounted(() => { if (!projects.projects.length) void projects.loadProjects() })
</script>

<template>
  <div><AppPageHeader eyebrow="WORKER CARE" title="工友助手" description="把专业整改要求转成尊重、简短、可执行的现场提醒。"><template #actions><span class="status-pill success"><span class="status-dot online" />知识库检索在线</span></template></AppPageHeader><div class="chat-layout"><section class="card chat-card"><header class="chat-head"><div><strong>现场安全小助手</strong><small>回答来自规范知识库检索，不替代安全员判断</small></div><span class="chat-status"><span class="status-dot online" />在线</span></header><div class="chat-body"><div v-for="(message, index) in messages" :key="`${message.time}-${index}`" class="chat-bubble" :class="{ mine: message.mine }">{{ message.text }}<div v-if="message.citations?.length" class="chat-citations"><span v-for="(citation, ci) in message.citations" :key="ci">来源：《{{ citation.source }}》{{ citation.article }}</span></div><small>{{ formatDateTime(message.time) }}<span v-if="message.source"> · {{ message.source }}</span></small></div><div v-if="sending" class="chat-bubble"><span class="loading-dots">正在组织回答…</span></div></div><div v-if="error" class="alert alert-error" role="alert" style="margin: 12px 14px 0">{{ error }}</div><form class="chat-input" @submit.prevent="send()"><input v-model.trim="question" aria-label="输入安全问题" placeholder="输入你想了解的安全问题" /><button class="primary-button button-small" type="submit" :disabled="sending || !question.trim()"><AppIcon name="arrow" :size="15" />发送</button></form></section><aside class="card"><div class="card-head"><div><p class="section-kicker">QUICK ASK</p><h3>快捷问题</h3></div><span>一键发送</span></div><div class="quick-questions"><button v-for="item in quickQuestions" :key="item" type="button" @click="send(item)">{{ item }}<AppIcon name="arrow" :size="14" /></button></div><VoiceInput :project-id="projectId" :disabled="sending" @text="onVoiceText" /><div class="mode-note"><AppIcon name="info" :size="16" /><div><strong>温和提醒</strong><span>高风险场景会提示暂停作业，但不会添加未提供的处罚或法规。</span></div></div></aside></div></div>
</template>
