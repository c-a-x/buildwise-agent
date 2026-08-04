import http from './http'
import type { ApiEnvelope } from '@/types/api'

export interface RuntimeStatus {
  app: string
  environment: string
  providers: {
    vision: string
    retrieval: string
    text: string
  }
  database: {
    status: 'connected' | 'unavailable'
    dialect: string
    persistent: boolean
  }
}

export const systemApi = {
  async health(): Promise<RuntimeStatus> {
    const response = await http.get<ApiEnvelope<RuntimeStatus>>('/health')
    return response.data.data
  },
}
