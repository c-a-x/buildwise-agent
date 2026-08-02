export interface ReportStatistics {
  incident_total: number
  risk_counts: Record<string, number>
  high_risk_total: number
  work_order_counts: Record<string, number>
  new_work_orders: number
  closed_work_orders: number
  pending_review_work_orders: number
  near_deadline_work_orders: number
  top_hazards: Array<{ hazard_type: string; count: number }>
}

export interface DailyReport {
  id: string
  project_id: string
  report_date: string
  statistics: ReportStatistics
  content: string
  generated_by: string
  is_ai_generated: boolean
  created_at: string
  updated_at: string
}
