import http from './http'
import type { ApiEnvelope } from '@/types/api'

export interface DashboardSummary {
  metrics: {
    today_incidents: number
    high_risk_incidents: number
    pending_work_orders: number
    pending_review_work_orders: number
    weekly_close_rate: number
    project_members: number
  }
  risk_distribution: Array<{ risk_level: string; count: number }>
  work_order_distribution: Array<{ status: string; count: number }>
  risk_trend: Array<{ date: string; count: number }>
  recent_tasks: Array<{ task_id: string; location: string; work_type: string; risk_level: string; status: string; created_at: string }>
  due_work_orders: Array<{ id: string; title: string; deadline: string; risk_level: string; status: string }>
}

export const dashboardApi = {
  async summary(projectId: string): Promise<DashboardSummary> {
    const response = await http.get<ApiEnvelope<DashboardSummary>>('/dashboard/summary', { params: { project_id: projectId } })
    return response.data.data
  },
}
