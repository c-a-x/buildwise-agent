import http from './http'
import type { ApiEnvelope } from '@/types/api'
import type { AuditLogListResponse } from '@/types/audit'

export interface AuditLogQuery {
  action?: string
  resource_type?: string
  limit?: number
  offset?: number
}

export const auditApi = {
  async logs(params?: AuditLogQuery): Promise<AuditLogListResponse> {
    const response = await http.get<ApiEnvelope<AuditLogListResponse>>('/audit/logs', { params })
    return response.data.data
  },
  async actions(): Promise<string[]> {
    const response = await http.get<ApiEnvelope<string[]>>('/audit/actions')
    return response.data.data
  },
}
