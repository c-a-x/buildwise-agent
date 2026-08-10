import http from './http'
import type { ApiEnvelope } from '@/types/api'
import type { CareCity, WeatherSnapshot, WellbeingAnalysisResult, WellbeingAnalyzeForm, WellbeingRecordSummary, WellbeingStatus, WellbeingTips } from '@/types/wellbeing'

export const wellbeingApi = {
  async analyze(payload: WellbeingAnalyzeForm): Promise<WellbeingAnalysisResult> {
    const response = await http.post<ApiEnvelope<WellbeingAnalysisResult>>('/care/analyze', payload)
    return response.data.data
  },
  async records(projectId?: string): Promise<WellbeingRecordSummary[]> {
    const response = await http.get<ApiEnvelope<WellbeingRecordSummary[]>>('/care/records', { params: projectId ? { project_id: projectId } : {} })
    return response.data.data
  },
  async record(recordId: string): Promise<WellbeingAnalysisResult> {
    const response = await http.get<ApiEnvelope<WellbeingAnalysisResult>>(`/care/records/${recordId}`)
    return response.data.data
  },
  async weather(city?: string): Promise<WeatherSnapshot> {
    const response = await http.get<ApiEnvelope<WeatherSnapshot>>('/care/weather', { params: city ? { city } : {} })
    return response.data.data
  },
  async cities(): Promise<CareCity[]> {
    const response = await http.get<ApiEnvelope<{ cities: CareCity[] }>>('/care/cities')
    return response.data.data.cities
  },
  async status(): Promise<WellbeingStatus> {
    const response = await http.get<ApiEnvelope<WellbeingStatus>>('/care/status')
    return response.data.data
  },
  async tips(): Promise<WellbeingTips> {
    const response = await http.get<ApiEnvelope<WellbeingTips>>('/care/tips')
    return response.data.data
  },
}
