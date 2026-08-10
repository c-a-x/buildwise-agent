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

// ---------- 四节一环保评估 ----------

export interface GreenMetricInput {
  key: string
  value: number | null
}

export interface DimensionInput {
  dimension: 'material' | 'water' | 'energy' | 'land' | 'env'
  metrics: GreenMetricInput[]
}

export interface GreenAssessmentForm {
  project_id: string
  title?: string
  area_m2?: number | null
  dimensions: DimensionInput[]
}

export interface MetricScore {
  key: string
  name: string
  value: number | null
  target: number
  direction: 'higher' | 'lower'
  score: number
}

export interface DimensionScore {
  dimension: string
  name: string
  score: number
  metrics: MetricScore[]
}

export interface GreenAssessmentResult {
  assessment_id: string
  project_id: string
  project_name: string
  title: string
  area_m2: number | null
  total_score: number
  level: string
  dimensions: DimensionScore[]
  is_simulated: boolean
  report_preview: string
  created_at: string
}

export interface GreenAssessmentSummary {
  assessment_id: string
  project_id: string
  project_name: string
  title: string
  total_score: number
  level: string
  is_simulated: boolean
  created_at: string
}

// ---------- 环保监测台账 ----------

export interface GreenEnvRecordForm {
  project_id: string
  record_date: string
  pm25: number | null
  pm10: number | null
  tsp: number | null
  noise_day_db: number | null
  noise_night_db: number | null
  cod_mg: number | null
  ss_mg: number | null
  ph: number | null
  solid_waste_t: number | null
}

export interface EnvThreshold {
  key: string
  name: string
  unit: string
  rule: 'above' | 'range'
  limit: number | null
  min: number | null
  max: number | null
}

export interface EnvAlert {
  key: string
  name: string
  value: number
  rule: string
  limit: number | null
  min: number | null
  max: number | null
}

export interface EnvRecord {
  record_id: string
  project_id: string
  project_name: string
  record_date: string
  pm25: number | null
  pm10: number | null
  tsp: number | null
  noise_day_db: number | null
  noise_night_db: number | null
  cod_mg: number | null
  ss_mg: number | null
  ph: number | null
  solid_waste_t: number | null
  has_alerts: boolean
  alerts: EnvAlert[]
  created_at: string
}

// ---------- 碳排趋势与目标 ----------

export interface GreenTargetForm {
  project_id: string
  target_intensity: number | null
  note?: string
}

export interface GreenTarget {
  project_id: string
  target_intensity: number | null
  note: string
  updated_at: string
}

export interface GreenTrendPoint {
  created_at: string
  total_emission: number
  area_m2: number
  intensity: number
}

export interface GreenTrendCurrent {
  intensity: number | null
  target_intensity: number | null
  grade: string
  gap_pct: number | null
}

export interface GreenTrend {
  project_id: string
  project_name: string
  points: GreenTrendPoint[]
  current: GreenTrendCurrent
}

// ---------- AI 优化建议 ----------

export interface GreenAdviceForm {
  project_id: string
  source_type: 'carbon' | 'assessment'
  analysis_id?: string | null
  assessment_id?: string | null
}

export interface GreenAdvice {
  advice: string
  is_simulated: boolean
  source_type: string
  generated_at: string
}
