import http from './http'
import type { ApiEnvelope } from '@/types/api'
import type { DailyReport } from '@/types/report'

export const reportsApi = {
  async generate(projectId: string, reportDate: string): Promise<DailyReport> {
    const response = await http.post<ApiEnvelope<DailyReport>>('/reports/daily/generate', { project_id: projectId, report_date: reportDate })
    return response.data.data
  },
  async get(projectId: string, reportDate: string): Promise<DailyReport> {
    const response = await http.get<ApiEnvelope<DailyReport>>('/reports/daily', { params: { project_id: projectId, report_date: reportDate } })
    return response.data.data
  },
  async history(projectId?: string): Promise<DailyReport[]> {
    const response = await http.get<ApiEnvelope<DailyReport[]>>('/reports', { params: projectId ? { project_id: projectId } : {} })
    return response.data.data
  },
}
