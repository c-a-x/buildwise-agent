import type { AgentStatus, RiskLevel } from './api'
import type { AgentTraceItem, Evidence, WorkOrderDraft } from './safety'

// 与 safety 的 Hazard 同构：字段名保持 hazard_*，质量语义体现在取值上
// （hazard_type=缺陷码 crack/leakage/abscission/corrosion/bulge、
//  hazard_name=缺陷中文名、risk_level=严重度）。
export interface QualityDefect {
  id: string
  hazard_type: string
  hazard_name: string
  description: string
  confidence: number
  risk_level: RiskLevel
  risk_score?: number | null
  bbox: number[] | null
  review_required: boolean
  source?: string | null
  regulation?: string | null
  suggestion?: string | null
  is_major?: boolean | null
  major_basis?: string | null
}

export interface QualityAnalysisResult {
  task_id: string
  project_id: string
  upload_id: string
  file_url: string
  annotated_url: string | null
  location: string
  work_type: string
  risk_level: RiskLevel
  defects: QualityDefect[]
  evidence: Evidence[]
  work_order_draft: WorkOrderDraft | null
  worker_message: string
  report_preview: string
  agent_trace: AgentTraceItem[]
  review_required: boolean
  is_simulated: boolean
  provider_info: Record<string, string>
}

export interface QualityTaskSummary {
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
