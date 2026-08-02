import http from './http'
import type { ApiEnvelope, RiskLevel, WorkOrderStatus } from '@/types/api'
import type { WorkOrder } from '@/types/workOrder'

export const workOrdersApi = {
  async list(params: { project_id?: string; status?: string; risk_level?: string } = {}): Promise<WorkOrder[]> {
    const response = await http.get<ApiEnvelope<WorkOrder[]>>('/work-orders', { params })
    return response.data.data
  },
  async get(id: string): Promise<WorkOrder> {
    const response = await http.get<ApiEnvelope<WorkOrder>>(`/work-orders/${id}`)
    return response.data.data
  },
  async create(taskId: string, assigneeUserId?: string): Promise<WorkOrder> {
    const response = await http.post<ApiEnvelope<WorkOrder>>('/work-orders', { task_id: taskId, assignee_user_id: assigneeUserId, confirm_ai_draft: true })
    return response.data.data
  },
  async updateStatus(id: string, status: WorkOrderStatus, note = ''): Promise<WorkOrder> {
    const response = await http.patch<ApiEnvelope<WorkOrder>>(`/work-orders/${id}/status`, { status, note })
    return response.data.data
  },
}
