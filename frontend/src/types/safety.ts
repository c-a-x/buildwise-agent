import type { AgentStatus, RiskLevel } from './api'

export interface Hazard {
  id: string
  hazard_type: string
  hazard_name: string
  description: string
  confidence: number
  risk_level: RiskLevel
  bbox: number[] | null
  review_required: boolean
  source?: string | null
  regulation?: string | null
  suggestion?: string | null
  is_major?: boolean | null
  major_basis?: string | null
}

export interface Evidence {
  id: string | null
  source: string
  article: string
  content: string
  score: number | null
}

export interface AgentTraceItem {
  agent: string
  status: AgentStatus
  message: string
  started_at?: string
  finished_at?: string
  duration_ms?: number
}

export interface WorkOrderDraft {
  task_id: string
  incident_id: string
  title: string
  problem_description: string
  risk_level: RiskLevel
  location: string
  deadline: string
  assignee_role: string
  rectification_requirements: string[]
  review_requirements: string[]
  worker_message: string
  ai_generated: boolean
  confirmed_by_human: boolean
  review_required: boolean
  is_simulated: boolean
}

export interface SafetyAnalysisResult {
  task_id: string
  project_id: string
  upload_id: string
  file_url: string
  annotated_url: string | null
  location: string
  work_type: string
  risk_level: RiskLevel
  hazards: Hazard[]
  evidence: Evidence[]
  work_order_draft: WorkOrderDraft | null
  worker_message: string
  report_preview: string
  agent_trace: AgentTraceItem[]
  review_required: boolean
  is_simulated: boolean
  provider_info: Record<string, string>
}

export interface SafetyTaskSummary {
  task_id: string
  project_id: string
  location: string
  work_type: string
  risk_level: RiskLevel
  status: AgentStatus
  incident_count: number
  is_simulated: boolean
  created_at: string
}

export interface DetectFrameHazard {
  id: string
  hazard_type: string
  hazard_name: string
  description: string
  confidence: number
  risk_level: RiskLevel
  bbox: number[] | null
  source?: string | null
}

export interface DetectFrameResult {
  available: boolean
  provider: string
  is_simulated: boolean
  risk_level: RiskLevel
  hazards: DetectFrameHazard[]
  latency_ms: number | null
  message: string
}
