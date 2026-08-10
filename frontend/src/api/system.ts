import http from './http'
import type { ApiEnvelope } from '@/types/api'

export type CapabilityStatus = 'available' | 'configured' | 'simulated' | 'not_configured' | 'unavailable'
export type CapabilityKey = 'vision' | 'retrieval' | 'text' | 'speech' | 'weather' | 'tts' | 'broadcast'

export interface ProviderCapability {
  key: CapabilityKey
  name: string
  provider: string
  status: CapabilityStatus
  is_simulated: boolean
  reason: string
  next_step: string
}

export interface RuntimeStatus {
  app: string
  environment: string
  providers: {
    vision: string
    retrieval: string
    text: string
  }
  database: {
    status: 'connected' | 'unavailable'
    dialect: string
    persistent: boolean
  }
  capabilities?: Partial<Record<CapabilityKey, ProviderCapability>>
}

export const systemApi = {
  async health(): Promise<RuntimeStatus> {
    const response = await http.get<ApiEnvelope<RuntimeStatus>>('/health')
    return response.data.data
  },
}
