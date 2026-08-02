export type Role =
  | 'admin'
  | 'project_manager'
  | 'safety_officer'
  | 'quality_inspector'
  | 'worker'

export type RiskLevel = 'normal' | 'low' | 'medium' | 'high' | 'critical'

export type WorkOrderStatus =
  | 'pending'
  | 'in_progress'
  | 'pending_review'
  | 'closed'

export type AgentStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped'

export interface ApiEnvelope<T> {
  success: boolean
  message: string
  data: T
  request_id: string
}

export interface ApiErrorPayload {
  success: false
  message: string
  error: {
    code: string
    details?: unknown
  }
  request_id: string
}
