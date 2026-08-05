import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import { knowledgeApi, type KnowledgeChatResult } from '@/api/knowledge'
import KnowledgeBaseView from '@/views/knowledge/KnowledgeBaseView.vue'

const chatResult: KnowledgeChatResult = {
  question: '高处作业临边防护有什么要求？',
  mode: 'rag_only',
  description: '离线检索拼装',
  answer: '【一、规范与标准条文】\n1. 《已授权项目制度》第12条 — 现场防护要求 — 进入现场必须佩戴安全帽。（相似度 0.95）\n【二、相关风险提示】\n命中风险类型「临边防护缺失」（missing_guardrail），建议落实责任角色 project_manager，在 2 小时内闭环整改。',
  citations: [
    { type: 'clause', document_id: 'DOC-001', source: '已授权项目制度', article: '第12条', title: '现场防护要求', score: 0.95 },
  ],
  retrieval: {
    clauses: { ready: true, count: 1 },
    risk_tip: { included: true, hazard_types: ['missing_guardrail'] },
    site: { included: false, project_id: null },
  },
  llm: { used: false, model: null, error: null },
}

describe('KnowledgeBaseView', () => {
  afterEach(() => vi.restoreAllMocks())

  it('shows provider, index counts, source-backed article, score, and metadata', async () => {
    vi.spyOn(knowledgeApi, 'indexStatus').mockResolvedValue({
      provider: 'chroma',
      indexed: true,
      document_count: 1,
      clause_count: 2,
      directory: 'storage/chroma',
      collection: 'buildwise-standards',
    })
    vi.spyOn(knowledgeApi, 'search').mockResolvedValue([
      {
        id: 'DOC-001:clause',
        document_id: 'DOC-001',
        title: '施工安全制度',
        source: '已授权项目制度',
        article: '第12条',
        category: '个人防护',
        content: '进入现场必须佩戴安全帽。',
        version: '2026',
        effective_date: '2026-01-01',
        score: 0.91,
        metadata: { hazard_types: ['no_helmet'] },
      },
    ])

    const wrapper = mount(KnowledgeBaseView)
    await flushPromises()

    expect(wrapper.text()).toContain('chroma')
    expect(wrapper.text()).toContain('2 条款')
    expect(wrapper.text()).toContain('已授权项目制度')
    expect(wrapper.text()).toContain('第12条')
    expect(wrapper.text()).toContain('0.91')
    expect(wrapper.text()).toContain('no_helmet')
  })

  it('asks a question and renders the rag_only answer, citations, and badge', async () => {
    vi.spyOn(knowledgeApi, 'indexStatus').mockResolvedValue({
      provider: 'local_keyword',
      indexed: true,
      document_count: 1,
      clause_count: 2,
      directory: null,
      collection: null,
    })
    vi.spyOn(knowledgeApi, 'search').mockResolvedValue([])
    const chatSpy = vi.spyOn(knowledgeApi, 'chat').mockResolvedValue(chatResult)

    const wrapper = mount(KnowledgeBaseView)
    await flushPromises()

    await wrapper.find('input[placeholder*="高处作业"]').setValue('高处作业临边防护有什么要求？')
    await wrapper.find('.chat-card button.primary-button').trigger('click')
    await flushPromises()

    expect(chatSpy).toHaveBeenCalledWith({ question: '高处作业临边防护有什么要求？' })
    expect(wrapper.text()).toContain('离线检索拼装')
    expect(wrapper.text()).toContain('【一、规范与标准条文】')
    expect(wrapper.text()).toContain('【二、相关风险提示】')
    expect(wrapper.text()).toContain('已授权项目制度')
    expect(wrapper.text()).toContain('第12条')
  })
})
