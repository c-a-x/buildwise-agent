import http from './http'
import type { ApiEnvelope } from '@/types/api'

export interface WorkerMessage {
  id: string
  question: string
  answer: string
  answer_source: string
  is_simulated: boolean
  created_at: string
}

export const workerCareApi = {
  async chat(projectId: string, question: string): Promise<WorkerMessage> {
    const response = await http.post<ApiEnvelope<WorkerMessage>>('/worker-care/chat', { project_id: projectId, question })
    return response.data.data
  },
}
