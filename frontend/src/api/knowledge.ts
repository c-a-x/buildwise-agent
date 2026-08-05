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

export interface KnowledgeChatPayload {
  question: string
  project_id?: string | null
  use_llm?: boolean | null
}

export interface KnowledgeChatCitation {
  type: string
  document_id: string
  source: string
  article: string
  title: string
  score: number
}

export interface KnowledgeChatResult {
  question: string
  mode: 'rag_only' | 'rag_llm' | string
  description: string
  answer: string
  citations: KnowledgeChatCitation[]
  retrieval: {
    clauses: { ready: boolean; count: number }
    risk_tip: { included: boolean; hazard_types: string[] }
    site: { included: boolean; project_id: string | null }
  }
  llm: { used: boolean; model: string | null; error: string | null }
}

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
  async chat(payload: KnowledgeChatPayload): Promise<KnowledgeChatResult> {
    const response = await http.post<ApiEnvelope<KnowledgeChatResult>>('/knowledge/chat', payload)
    return response.data.data
  },
}
