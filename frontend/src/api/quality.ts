import http from './http'
import type { ApiEnvelope } from '@/types/api'
import type { QualityAnalysisResult, QualityTaskSummary } from '@/types/quality'

export interface QualityAnalyzePayload {
  project_id: string
  location: string
  work_type: string
  description?: string
  demo_scenario?: string
}

export const qualityApi = {
  async analyze(file: File, payload: QualityAnalyzePayload): Promise<QualityAnalysisResult> {
    const form = new FormData()
    form.append('image', file)
    Object.entries(payload).forEach(([key, value]) => {
      if (value) form.append(key, value)
    })
    const response = await http.post<ApiEnvelope<QualityAnalysisResult>>('/quality/analyze', form)
    return response.data.data
  },
  async tasks(projectId?: string): Promise<QualityTaskSummary[]> {
    const response = await http.get<ApiEnvelope<QualityTaskSummary[]>>('/quality/tasks', { params: projectId ? { project_id: projectId } : {} })
    return response.data.data
  },
  async task(taskId: string): Promise<QualityAnalysisResult> {
    const response = await http.get<ApiEnvelope<QualityAnalysisResult>>(`/quality/tasks/${taskId}`)
    return response.data.data
  },
}
