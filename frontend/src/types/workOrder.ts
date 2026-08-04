import type { RiskLevel, WorkOrderStatus } from './api'

export interface WorkOrderEvent {
  id: string
  event_type: string
  from_status: WorkOrderStatus | null
  to_status: WorkOrderStatus | null
  note: string
  actor_user_id: string
  created_at: string
}

export interface WorkOrder {
  id: string
  project_id: string
  incident_id: string
  source_task_id: string
  title: string
  problem_description: string
  risk_level: RiskLevel
  location: string
  assignee_user_id: string
  created_by: string
  deadline: string
  status: WorkOrderStatus
  rectification_requirements: string[]
  review_requirements: string[]
  worker_message: string
  ai_generated: boolean
  confirmed_by_human: boolean
  closed_at: string | null
  created_at: string
  updated_at: string
  events: WorkOrderEvent[]
  file_url: string | null
  annotated_url: string | null
  evidence: Array<{ id?: string; source: string; article: string; content: string; score?: number | null }>
}
