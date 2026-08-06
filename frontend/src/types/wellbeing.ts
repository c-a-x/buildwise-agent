export interface WellbeingAnalyzeForm {
  project_id: string
  temperature_c: number
  humidity_pct: number
  condition: string
  description?: string
}

export interface WellbeingTip {
  id: string
  text: string
}

export interface FirstAidStage {
  stage: string
  symptoms: string
  action: string
}

export interface Facility {
  name: string
  location: string
  hours: string
  note: string
}

export interface HeatLevel {
  level: 'none' | 'yellow' | 'orange' | 'red'
  name: string
  advice: string
}

export interface WellbeingAnalysisResult {
  analysis_id: string
  project_id: string
  project_name: string
  created_at: string
  heat_level: 'none' | 'yellow' | 'orange' | 'red'
  heat_level_name: string
  advice: string
  restriction: string
  risk_index: number
  risk_tier: string
  heat_index: number | null
  uv: string
  condition: string
  temperature_c: number
  humidity_pct: number
  description: string
  reminders: WellbeingTip[]
  allowance: string
  special_groups: string
  first_aid: FirstAidStage[]
  facilities: Facility[]
  broadcast: boolean
  is_simulated: boolean
  source: string
  rules_version: string
}

export interface WellbeingRecordSummary {
  analysis_id: string
  project_id: string
  project_name: string
  heat_level: 'none' | 'yellow' | 'orange' | 'red'
  risk_index: number
  heat_index: number | null
  is_simulated: boolean
  created_at: string
}

export interface WeatherSnapshot {
  available: boolean
  reason: string | null
  provider: string | null
  temperature_c: number | null
  humidity_pct: number | null
  condition: string | null
  city: string | null
  observed_at: string | null
  is_simulated: boolean
}

export interface WellbeingTips {
  version: string
  source: string
  heat_levels: HeatLevel[]
  restriction: Record<string, string>
  special_groups: string
  allowance: string
  tips: WellbeingTip[]
  first_aid: FirstAidStage[]
  facilities: Facility[]
  load_error: string
}
