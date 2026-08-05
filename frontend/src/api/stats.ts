import http from './http'
import type { ApiEnvelope } from '@/types/api'

export interface AnomalySample {
  date: string
  count: number
  z: number
  anomaly: boolean
}

export interface AnomalyResult {
  available: boolean
  reason?: string
  project_id: string
  module: 'safety' | 'quality'
  days: number
  z_threshold: number
  total_days: number
  mean: number
  std: number
  anomaly_days: number
  ratio: number
  samples: AnomalySample[]
}

export const statsApi = {
  async anomalies(projectId: string, module: 'safety' | 'quality' = 'safety', days = 30, zThreshold = 2.5): Promise<AnomalyResult> {
    const response = await http.get<ApiEnvelope<AnomalyResult>>('/stats/anomalies', { params: { project_id: projectId, module, days, z_threshold: zThreshold } })
    return response.data.data
  },
}
