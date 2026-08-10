import http from './http'
import type { ApiEnvelope } from '@/types/api'
import type { CarbonAnalysisResult, CarbonAnalysisSummary, EnvRecord, EnvThreshold, GreenAdvice, GreenAdviceForm, GreenAnalyzeForm, GreenAssessmentForm, GreenAssessmentResult, GreenAssessmentSummary, GreenBenchmark, GreenEnvRecordForm, GreenFactor, GreenReference, GreenTarget, GreenTargetForm, GreenTrend } from '@/types/green'

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
  // ---------- 四节一环保评估 ----------
  async submitAssessment(payload: GreenAssessmentForm): Promise<GreenAssessmentResult> {
    const response = await http.post<ApiEnvelope<GreenAssessmentResult>>('/green/assessments', payload)
    return response.data.data
  },
  async assessments(projectId?: string): Promise<GreenAssessmentSummary[]> {
    const response = await http.get<ApiEnvelope<GreenAssessmentSummary[]>>('/green/assessments', { params: projectId ? { project_id: projectId } : {} })
    return response.data.data
  },
  async assessment(assessmentId: string): Promise<GreenAssessmentResult> {
    const response = await http.get<ApiEnvelope<GreenAssessmentResult>>(`/green/assessments/${assessmentId}`)
    return response.data.data
  },
  async downloadAssessmentReport(assessmentId: string): Promise<Blob> {
    const response = await http.get<Blob>(`/green/assessments/${assessmentId}/report`, { responseType: 'blob' })
    return response.data
  },
  // ---------- 环保监测台账 ----------
  async saveEnvRecord(payload: GreenEnvRecordForm): Promise<EnvRecord> {
    const response = await http.post<ApiEnvelope<EnvRecord>>('/green/env-records', payload)
    return response.data.data
  },
  async envRecords(params?: { project_id?: string; start_date?: string; end_date?: string; alert_only?: boolean }): Promise<EnvRecord[]> {
    const response = await http.get<ApiEnvelope<EnvRecord[]>>('/green/env-records', { params })
    return response.data.data
  },
  async envThresholds(): Promise<EnvThreshold[]> {
    const response = await http.get<ApiEnvelope<EnvThreshold[]>>('/green/env-records/thresholds')
    return response.data.data
  },
  // ---------- 碳排趋势与目标 ----------
  async trend(projectId: string): Promise<GreenTrend> {
    const response = await http.get<ApiEnvelope<GreenTrend>>('/green/trend', { params: { project_id: projectId } })
    return response.data.data
  },
  async target(projectId: string): Promise<GreenTarget> {
    const response = await http.get<ApiEnvelope<GreenTarget>>('/green/target', { params: { project_id: projectId } })
    return response.data.data
  },
  async saveTarget(payload: GreenTargetForm): Promise<GreenTarget> {
    const response = await http.put<ApiEnvelope<GreenTarget>>('/green/target', payload)
    return response.data.data
  },
  // ---------- AI 优化建议 ----------
  async advice(payload: GreenAdviceForm): Promise<GreenAdvice> {
    const response = await http.post<ApiEnvelope<GreenAdvice>>('/green/advice', payload)
    return response.data.data
  },
}
