import http from './http'
import type { ApiEnvelope } from '@/types/api'

export interface WorkerCitation {
  source: string
  article?: string
  title?: string
}

export interface WorkerMessage {
  id: string
  question: string
  answer: string
  answer_source: string
  is_simulated: boolean
  citations?: WorkerCitation[]
  created_at: string
}

export interface TranscribeResult {
  available: boolean
  text: string
  reason: string | null
  provider: string
}

export const workerCareApi = {
  async chat(projectId: string, question: string): Promise<WorkerMessage> {
    const response = await http.post<ApiEnvelope<WorkerMessage>>('/worker-care/chat', { project_id: projectId, question })
    return response.data.data
  },
  async transcribe(projectId: string, audio: Blob): Promise<TranscribeResult> {
    const form = new FormData()
    form.append('project_id', projectId)
    form.append('audio', audio, 'voice.webm')
    const response = await http.post<ApiEnvelope<TranscribeResult>>('/worker-care/transcribe', form)
    return response.data.data
  },
}
