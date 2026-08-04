import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import { knowledgeApi } from '@/api/knowledge'
import KnowledgeBaseView from '@/views/knowledge/KnowledgeBaseView.vue'

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
})
