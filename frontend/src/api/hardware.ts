import http from './http'
import type { ApiEnvelope } from '@/types/api'
import type { HardwareTelemetry } from '@/types/hardware'

export const hardwareApi = {
  async latest(): Promise<HardwareTelemetry | null> {
    const response = await http.get<ApiEnvelope<HardwareTelemetry | null>>('/hardware/telemetry/latest', { timeout: 2500 })
    return response.data.data
  },
}
