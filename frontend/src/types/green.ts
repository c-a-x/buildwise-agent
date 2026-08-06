export interface GreenItemInput {
  code: string
  name: string
  quantity: number
  unit: string
  note?: string
}

export interface GreenAnalyzeForm {
  project_id: string
  area_m2: number | null
  scope: string
  materials: GreenItemInput[]
  transport: GreenItemInput[]
  energy: GreenItemInput[]
}

export interface CarbonItem {
  category: 'material' | 'energy' | 'transport'
  stage: string
  stage_name: string
  code: string
  name: string
  unit: string
  quantity: number
  emission_factor: number | null
  factor_unit: string
  emission: number
  factor_source: string
  verified: boolean
  factor_missing: boolean
  note: string
}

export interface CarbonStage {
  stage: string
  stage_name: string
  emission: number
  share: number
  items_count: number
}

export interface CarbonContributor {
  code: string
  name: string
  category: string
  stage: string
  emission: number
  share: number
}

export interface CarbonAnalysisResult {
  analysis_id: string
  project_id: string
  project_name: string
  created_at: string
  area_m2: number | null
  scope: string
  total_emission: number
  unit: string
  intensity: number | null
  stages: CarbonStage[]
  items: CarbonItem[]
  top_contributors: CarbonContributor[]
  suggestions: string[]
  factor_version: string
  has_unverified_factors: boolean
  factor_warnings: string[]
  report_preview: string
  is_simulated: boolean
}

export interface CarbonAnalysisSummary {
  analysis_id: string
  project_id: string
  project_name: string
  area_m2: number | null
  scope: string
  total_emission: number
  is_simulated: boolean
  has_unverified_factors: boolean
  created_at: string
}

export interface GreenFactor {
  code: string
  category: 'material' | 'energy' | 'transport'
  name: string
  unit: string
  factor: number
  factor_unit: string
  source: string
  year: number | null
  verified: boolean
  note: string
}

export interface BenchmarkItem {
  rank: number
  project_id: string
  project_name: string
  intensity: number | null
  z: number
  better_than_pct: number
}

export interface GreenBenchmark {
  available: boolean
  reason: string | null
  count: number
  metric: string
  unit: string
  mean: number | null
  std: number | null
  current: BenchmarkItem | null
  items: BenchmarkItem[]
}

export interface ReferenceMetric {
  code: string
  name: string
  value: string
  unit: string
  year: number | null
  source: string
  note: string
}

export interface ReferenceGroup {
  category: string
  name: string
  items: ReferenceMetric[]
}

export interface GreenReference {
  version: string
  updated_at: string
  source_note: string
  groups: ReferenceGroup[]
}
