import http from './http'
import type { ApiEnvelope } from '@/types/api'
import type { CarbonAnalysisResult, CarbonAnalysisSummary, GreenAnalyzeForm, GreenBenchmark, GreenFactor, GreenReference } from '@/types/green'

export const greenApi = {
  async analyze(payload: GreenAnalyzeForm): Promise<CarbonAnalysisResult> {
    const response = await http.post<ApiEnvelope<CarbonAnalysisResult>>('/green/analyze', payload)
    return response.data.data
  },
  async analyses(projectId?: string): Promise<CarbonAnalysisSummary[]> {
    const response = await http.get<ApiEnvelope<CarbonAnalysisSummary[]>>('/green/analyses', { params: projectId ? { project_id: projectId } : {} })
    return response.data.data
  },
  async analysis(analysisId: string): Promise<CarbonAnalysisResult> {
    const response = await http.get<ApiEnvelope<CarbonAnalysisResult>>(`/green/analyses/${analysisId}`)
    return response.data.data
  },
  async downloadReport(analysisId: string): Promise<Blob> {
    const response = await http.get<Blob>(`/green/analyses/${analysisId}/report`, { responseType: 'blob' })
    return response.data
  },
  async factors(): Promise<GreenFactor[]> {
    const response = await http.get<ApiEnvelope<GreenFactor[]>>('/green/factors')
    return response.data.data
  },
  async benchmark(projectId?: string): Promise<GreenBenchmark> {
    const response = await http.get<ApiEnvelope<GreenBenchmark>>('/green/benchmark', { params: projectId ? { project_id: projectId } : {} })
    return response.data.data
  },
  async reference(): Promise<GreenReference> {
    const response = await http.get<ApiEnvelope<GreenReference>>('/green/reference')
    return response.data.data
  },
}
