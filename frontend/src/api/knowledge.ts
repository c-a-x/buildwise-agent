import http from './http'
import type { ApiEnvelope } from '@/types/api'

export interface KnowledgeIndexStatus {
  provider: 'local_keyword' | 'chroma' | string
  indexed: boolean
  document_count: number
  clause_count: number
  directory: string | null
  collection: string | null
}

export interface KnowledgeSearchResult {
  id: string
  document_id: string
  title: string
  source: string
  article: string
  version: string
  category: string
  effective_date: string | null
  content: string
  metadata: Record<string, unknown>
  status?: string
  created_at?: string
  score?: number
}

export type KnowledgeDocument = KnowledgeSearchResult

export const knowledgeApi = {
  async search(query = ''): Promise<KnowledgeSearchResult[]> {
    const response = await http.get<ApiEnvelope<KnowledgeSearchResult[]>>('/knowledge/search', { params: { q: query } })
    return response.data.data
  },
  async indexStatus(): Promise<KnowledgeIndexStatus> {
    const response = await http.get<ApiEnvelope<KnowledgeIndexStatus>>('/knowledge/index/status')
    return response.data.data
  },
  async reindex(): Promise<KnowledgeIndexStatus> {
    const response = await http.post<ApiEnvelope<KnowledgeIndexStatus>>('/knowledge/reindex')
    return response.data.data
  },
}
