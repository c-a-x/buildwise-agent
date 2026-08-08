<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { getApiError } from '@/api/http'
import { knowledgeApi, type KnowledgeChatResult, type KnowledgeIndexStatus, type KnowledgeSearchResult } from '@/api/knowledge'
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageHeader from '@/components/common/AppPageHeader.vue'
import AppState from '@/components/common/AppState.vue'

const query = ref('')
const documents = ref<KnowledgeSearchResult[]>([])
const indexStatus = ref<KnowledgeIndexStatus | null>(null)
const loading = ref(false)
const rebuilding = ref(false)
const error = ref('')
const chatQuestion = ref('')
const chatResult = ref<KnowledgeChatResult | null>(null)
const chatting = ref(false)
const chatError = ref('')

function formatMetadata(metadata: Record<string, unknown>): string {
  return JSON.stringify(metadata) || '无附加元数据'
}

async function askChat(): Promise<void> {
  const question = chatQuestion.value.trim()
  if (!question) return
  chatting.value = true
  chatError.value = ''
  try {
    chatResult.value = await knowledgeApi.chat({ question })
  } catch (cause) {
    chatError.value = getApiError(cause)
  } finally {
    chatting.value = false
  }
}

async function loadIndexStatus(): Promise<void> {
  indexStatus.value = await knowledgeApi.indexStatus()
}

async function search(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    documents.value = await knowledgeApi.search(query.value)
  } catch (cause) {
    error.value = getApiError(cause)
  } finally {
    loading.value = false
  }
}

async function refresh(): Promise<void> {
  error.value = ''
  loading.value = true
  try {
    const [status, results] = await Promise.all([knowledgeApi.indexStatus(), knowledgeApi.search(query.value)])
    indexStatus.value = status
    documents.value = results
  } catch (cause) {
    error.value = getApiError(cause)
  } finally {
    loading.value = false
  }
}

async function rebuildIndex(): Promise<void> {
  rebuilding.value = true
  error.value = ''
  try {
    await knowledgeApi.reindex()
    await Promise.all([loadIndexStatus(), search()])
  } catch (cause) {
    error.value = getApiError(cause)
  } finally {
    rebuilding.value = false
  }
}

onMounted(refresh)
</script>

<template>
  <div>
    <AppPageHeader eyebrow="KNOWLEDGE BASE" title="规范知识库" description="检索结果必须来自已导入的授权条款；系统不会用生成内容填充不存在的规范依据。">
      <template #actions>
        <button class="secondary-button" type="button" :disabled="rebuilding" @click="rebuildIndex">
          <AppIcon name="refresh" :size="16" />{{ rebuilding ? '重建中…' : '重建索引' }}
        </button>
        <button class="secondary-button" type="button" disabled><AppIcon name="upload" :size="16" />上传文档 · 命令行导入</button>
      </template>
    </AppPageHeader>

    <section class="knowledge-index-panel">
      <div class="knowledge-index-heading">
        <div>
          <p class="section-kicker">INDEX STATUS</p>
          <h2>检索索引状态</h2>
        </div>
        <span v-if="indexStatus" class="status-pill" :class="indexStatus.indexed ? 'success' : 'warning'">{{ indexStatus.indexed ? '已建立' : '待导入' }}</span>
      </div>
      <div v-if="indexStatus" class="knowledge-index-stats">
        <div><small>Provider</small><strong class="mono">{{ indexStatus.provider }}</strong></div>
        <div><small>文档数</small><strong>{{ indexStatus.document_count }} 文档</strong></div>
        <div><small>条款数</small><strong>{{ indexStatus.clause_count }} 条款</strong></div>
        <div><small>Collection</small><strong class="mono">{{ indexStatus.collection || 'local file' }}</strong></div>
      </div>
      <p v-else class="muted-copy">正在读取索引状态…</p>
    </section>

    <section class="card">
      <div class="knowledge-search">
        <label class="search-field wide"><AppIcon name="search" :size="17" /><input v-model.trim="query" placeholder="搜索安全帽、临边、防护栏杆…" @keyup.enter="search" /></label>
        <button class="primary-button" type="button" :disabled="loading" @click="search">{{ loading ? '检索中…' : '搜索规范' }}</button>
      </div>
      <div v-if="error" class="alert alert-error" role="alert">{{ error }}</div>
      <AppState v-if="loading" type="loading" title="正在检索规范索引" />
      <AppState v-else-if="!documents.length" title="没有匹配的规范条目" description="请换一个关键词。系统不会用生成内容填充不存在的条款。" />
      <div v-else class="knowledge-grid">
        <article v-for="document in documents" :key="document.id || `${document.document_id}-${document.article}`" class="knowledge-card">
          <div class="knowledge-card-head">
            <span class="status-pill success">{{ document.category }}</span>
            <span class="mono">{{ document.document_id }}</span>
          </div>
          <h3>{{ document.title }}</h3>
          <p class="knowledge-source">{{ document.source }} · {{ document.article }} · {{ document.version || '未标注版本' }}</p>
          <p>{{ document.content }}</p>
          <div class="knowledge-result-meta">
            <span v-if="document.score !== undefined">相似度 {{ document.score.toFixed(2) }}</span>
            <span>{{ formatMetadata(document.metadata) }}</span>
          </div>
          <footer>来源条款 · {{ document.article }}</footer>
        </article>
      </div>
    </section>

    <section class="card chat-card">
      <div class="card-head">
        <div><p class="section-kicker">ASK</p><h3>规范问答</h3></div>
        <span v-if="chatResult" class="status-pill" :class="chatResult.mode === 'rag_llm' ? 'dark' : 'warning'">{{ chatResult.mode === 'rag_llm' ? 'RAG + LLM' : '离线检索拼装' }}</span>
      </div>
      <div class="knowledge-search">
        <label class="search-field wide"><AppIcon name="spark" :size="17" /><input v-model.trim="chatQuestion" placeholder="提问：如 高处作业临边防护有什么要求？" @keyup.enter="askChat" /></label>
        <button class="primary-button" type="button" :disabled="chatting || !chatQuestion.trim()" @click="askChat">{{ chatting ? '检索拼装中…' : '提问' }}</button>
      </div>
      <p class="helper-text">回答由已导入的授权条款离线拼装，命中风险类型会附带责任人建议；未配置 LLM 时自动使用离线模式，不会伪造条款。</p>
      <div v-if="chatError" class="alert alert-error" role="alert">{{ chatError }}</div>
      <div v-if="chatResult" class="chat-answer">
        <pre class="chat-sections">{{ chatResult.answer }}</pre>
        <div v-if="chatResult.citations.length" class="chat-citations">
          <span v-for="(citation, index) in chatResult.citations" :key="index" class="citation-chip" :title="`相似度 ${citation.score.toFixed(2)}`">{{ citation.source }} · {{ citation.article }}</span>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.chat-card { margin-top: 18px; }
.chat-answer { margin-top: 12px; }
.chat-sections { margin: 0; padding: 14px 16px; border-radius: 10px; background: var(--surface-soft); white-space: pre-wrap; overflow-wrap: anywhere; color: var(--text-soft); font-family: inherit; font-size: 12px; line-height: 1.9; }
.chat-citations { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.citation-chip { display: inline-flex; align-items: center; padding: 3px 10px; border-radius: 999px; background: var(--primary-soft); color: var(--primary-deep); font-size: 11px; font-weight: 600; }
</style>
