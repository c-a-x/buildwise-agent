<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { getApiError } from '@/api/http'
import { knowledgeApi, type KnowledgeDocument } from '@/api/knowledge'
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageHeader from '@/components/common/AppPageHeader.vue'
import AppState from '@/components/common/AppState.vue'

const query = ref('')
const documents = ref<KnowledgeDocument[]>([])
const loading = ref(false)
const error = ref('')
async function search(): Promise<void> { loading.value = true; error.value = ''; try { documents.value = await knowledgeApi.search(query.value) } catch (cause) { error.value = getApiError(cause) } finally { loading.value = false } }
onMounted(search)
</script>

<template><div><AppPageHeader eyebrow="KNOWLEDGE BASE" title="规范知识库" description="内置安全条款支持关键词检索；检索不到时系统会明确提示，不编造规范依据。"><template #actions><button class="secondary-button" type="button" disabled><AppIcon name="upload" :size="16" />上传文档 · 后续版本</button></template></AppPageHeader><section class="card"><div class="knowledge-search"><label class="search-field wide"><AppIcon name="search" :size="17" /><input v-model.trim="query" placeholder="搜索安全帽、临边、防护栏杆…" @keyup.enter="search" /></label><button class="primary-button" type="button" :disabled="loading" @click="search">{{ loading ? '检索中…' : '搜索规范' }}</button></div><div v-if="error" class="alert alert-error" role="alert">{{ error }}</div><AppState v-if="loading" type="loading" title="正在检索内置规范" /><AppState v-else-if="!documents.length" title="没有匹配的规范条目" description="请换一个关键词。系统不会用生成内容填充不存在的条款。" /><div v-else class="knowledge-grid"><article v-for="document in documents" :key="document.id" class="knowledge-card"><div class="knowledge-card-head"><span class="status-pill success">{{ document.category }}</span><span class="mono">{{ document.id }}</span></div><h3>{{ document.title }}</h3><p class="knowledge-source">{{ document.source }} · {{ document.version }}</p><p>{{ document.content }}</p><footer>{{ document.id }} · 内置条目</footer></article></div></section></div></template>
