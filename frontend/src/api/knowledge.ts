import http from './http'
import type { ApiEnvelope } from '@/types/api'

export interface KnowledgeDocument {
  id: string
  title: string
  source: string
  version: string
  category: string
  content: string
  status: string
  created_at: string
}

export const knowledgeApi = {
  async search(query = ''): Promise<KnowledgeDocument[]> {
    const response = await http.get<ApiEnvelope<KnowledgeDocument[]>>('/knowledge/search', { params: { q: query } })
    return response.data.data
  },
}
