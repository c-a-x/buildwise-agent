import http from './http'
import type { ApiEnvelope } from '@/types/api'
import type { ModuleStatus } from '@/types/module'

export const modulesApi = {
  async list(): Promise<ModuleStatus[]> {
    const response = await http.get<ApiEnvelope<ModuleStatus[]>>('/modules')
    return response.data.data
  },
}
